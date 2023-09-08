#!/usr/bin/env python3
import os.path
import subprocess
import json
import math
import string
import logging
import argparse
import re
from typing import Union, Dict, Any, List, Tuple, Set

NAME_KEY = "name"
STATUS_KEY = "status"
ID_KEY = "id"
BSPC_KEY = "bspc_id"
EDID_KEY = "edid"

CONNECTED_STATUS = "connected"
DISCONNECTED_STATUS = "disconnected"
UNKNOWN_CONNECTION_STATUS = "unknown connection"
__debug_is_on = False

Monitor = Dict[str, str]
MonitorData = Monitor
BspcMonitor = Monitor
Monitors = List[Monitor]
Actions = Tuple[Monitors, Monitors, Monitors]


def get_resolution_and_position(status_text) -> Union[None, Dict[str, Union[str, Any]]]:
    test_regex = re.compile(r"(?P<status>disconnected|unknown connection|connected)"
                            + r"(?:\s*(?P<primary>primary)?"
                            + r"\s*(?P<width>[0-9]+)x(?P<height>[0-9]+)"
                            + r"\+(?P<xoffset>-?[0-9]+)\+(?P<yoffset>-?[0-9]+))?")
    test_match = test_regex.match(status_text)
    if test_match is None:
        logging.debug('get_resolution_and_position: found no header information')
        return None
    logging.debug('get_resolution_and_position: found %s', test_match.groups())
    return test_match.groupdict()


def get_status(status_text: str) -> str:
    if status_text.startswith(CONNECTED_STATUS):
        return CONNECTED_STATUS
    if status_text.startswith(DISCONNECTED_STATUS):
        return DISCONNECTED_STATUS
    if status_text.startswith(UNKNOWN_CONNECTION_STATUS):
        return UNKNOWN_CONNECTION_STATUS
    return UNKNOWN_CONNECTION_STATUS


def is_connected(entry: Monitor) -> bool:
    return entry[STATUS_KEY] == CONNECTED_STATUS


def get_monitors_from_bspc() -> BspcMonitor:
    found_randrids: BspcMonitor = dict()

    result = subprocess.run(['bspc', 'query', '-M'], stdout=subprocess.PIPE)
    monitors = result.stdout.decode('utf-8').split()

    for monitor in monitors:
        result = subprocess.run(['bspc', 'query', '-m', monitor, '-T'],
                                stdout=subprocess.PIPE)
        monitor_information = result.stdout.decode('utf-8')
        decoded_info = json.loads(monitor_information)
        if 'randrId' in decoded_info:
            found_randrids[monitor] = str(decoded_info['randrId'])

    logging.debug('get_monitors_from_bspc: found rand ids = %s', repr(found_randrids))

    return found_randrids


def get_xrandr_sections() -> list[str]:
    result = subprocess.run(['xrandr', '--verbose'], stdout=subprocess.PIPE)
    xrandr_output = result.stdout.decode('utf-8')

    current = list()
    start_index = index = 0
    output_length = len(xrandr_output)
    while index != -1:
        index = xrandr_output.find("\n", index)
        if index != -1:
            if not index + 1 >= output_length:
                if xrandr_output[index + 1].isalpha():
                    current.append(xrandr_output[start_index: index])
                    start_index = index + 1
                if xrandr_output[index + 1].isspace():
                    pass
            else:
                current.append(xrandr_output[start_index: index])

            index = index + 1
    return current


def parse_identifier(line: str) -> MonitorData:
    return {ID_KEY: str(int(line.strip().split()[1], 16))}


def parse_header(line: str) -> MonitorData:
    splitted = line.split(' ', 1)
    more_info_dict = None
    if not splitted[0].lower().startswith("screen"):
        more_info_dict = get_resolution_and_position(splitted[1])
    if more_info_dict is not None:
        more_info_dict[NAME_KEY] = splitted[0]
        return more_info_dict
    return {NAME_KEY: splitted[0], STATUS_KEY: get_status(splitted[1])}


def parse_edid(num: int, lines: list[str]) -> Tuple[MonitorData, Set]:
    skippable_lines = set()
    current_edid = list()
    depth = lines[num].count('\t')
    line_index = num + 1
    splitted_edid = lines[num].strip().split(':')
    if len(splitted_edid) > 1:
        current_edid.append(splitted_edid[1])
    while lines[line_index].startswith('\t' * (depth + 1)):
        skippable_lines.add(line_index)
        current_edid.append(lines[line_index].strip())
        line_index = line_index + 1
    return {EDID_KEY: ''.join(current_edid)}, skippable_lines


def get_monitors_from_xrandr(found_randrids: BspcMonitor) -> Monitors:
    current: Monitor = dict()
    xrandr_results: Monitors = list()
    xrandr_sections = get_xrandr_sections()

    for xrandr_entry in xrandr_sections:
        skippable_lines = set()
        xrandr_info = xrandr_entry.split('\n')
        for num, line in enumerate(xrandr_info):
            if num in skippable_lines:
                continue

            if not line.startswith('\t') and not line.startswith(' '):
                current.update(parse_header(line))

            elif line.startswith('\t'):
                if line.startswith('\tIdentifier:'):
                    current.update(parse_identifier(line))

                if line.startswith('\tEDID:'):
                    edid_dict, traversed_lines = parse_edid(num, xrandr_info)
                    current.update(edid_dict)
                    skippable_lines.update(traversed_lines)

        if ID_KEY in current:
            for key in found_randrids:
                if found_randrids[key] == current[ID_KEY]:
                    current[BSPC_KEY] = key
            xrandr_results.append(current)
        current = dict()
    return xrandr_results


def separate_into_actions(xrandr_results: Monitors) -> Actions:
    to_add = list()
    to_chill = list()
    to_remove = list()

    for row in xrandr_results:
        if is_connected(row):
            if not check_lid_closed(str(row.get(NAME_KEY))):
                to_add.append(row)
            else:
                to_chill.append(row)
        else:
            to_remove.append(row)
    return (to_add, to_chill, to_remove)


def get_monitors_actions() -> Actions:
    found_randrids = get_monitors_from_bspc()

    xrandr_results = get_monitors_from_xrandr(found_randrids)
    xrandr_results = filter_monitors_without_bspc_id(xrandr_results)

    return separate_into_actions(xrandr_results)


def get_primary_monitor(monitors: Monitors) -> Union[Monitor, None]:
    for x in monitors:
        if x['primary'] is not None:
            return x
    return None


def is_monitor_in_list(x: Monitor, y: Monitors) -> bool:
    return any((x[NAME_KEY] == m[NAME_KEY] for m in y))


def is_monitor_primary(x: Monitor) -> bool:
    return x['primary'] is not None


def get_boss_monitor(x: Monitor, y: Monitors) -> Monitor:
    return sorted([x] + y, key=lambda x: (int(x.get('width', 4096)), int(x.get('height', 128))), reverse=True)[0]


def special_rules(actions: Actions) -> Actions:
    new_add: Monitors = list()
    new_meh: Monitors = list()
    for x in actions[0]:
        if is_monitor_in_list(x, new_meh):
            continue

        found_special = [z for z in actions[0] if (not x[NAME_KEY] == z[NAME_KEY]) and x['xoffset'] == z['xoffset'] and x['yoffset'] == z['yoffset'] and (not is_monitor_in_list(z, new_meh))]

        if len(found_special) == 0:
            if not is_monitor_in_list(x, new_add):
                new_add.append(x)
            continue

        primary_monitor = get_primary_monitor([x] + found_special)

        if primary_monitor is None:
            master_monitor = get_boss_monitor(x, found_special)

            if not is_monitor_in_list(master_monitor, new_add):
                new_add.append(master_monitor)

            for z in found_special:
                if not is_monitor_in_list(z, new_meh) and not is_monitor_in_list(z, new_add):
                    new_meh.append(z)

            continue

        if is_monitor_primary(x):
            new_add.append(x)
        elif not is_monitor_in_list(x, new_meh):
            new_meh.append(x)

        for z in found_special:
            if is_monitor_primary(z):
                new_add.append(z)
                continue

            if not is_monitor_in_list(z, new_meh):
                new_meh.append(z)

    return (new_add, new_meh, actions[2])


def debug_overridden_execute_command(action_cmd: List[str]) -> None:
    logging.debug('execute_command called with: %s', ' '.join(action_cmd))
    if not __debug_is_on:
        subprocess.run(action_cmd)


def tab_data_str(x: list[Any]) -> str:
    return '\n'.join(('\t\t{}'.format(z) for z in x))


def execute_bspc_commands(actions: Actions) -> None:
    debug_on = __debug_is_on
    monitor_id = 1
    if debug_on:
        logging.debug("before_special_rules:\n"
                      + "\tafter_special_rules[0]:\n%s\n"
                      + "\tafter_special_rules[1]:\n%s\n"
                      + "\tafter_special_rules[2]:\n%s",
                      tab_data_str(actions[0]),
                      tab_data_str(actions[1]),
                      tab_data_str(actions[2]))
    actions = special_rules(actions)

    if debug_on:
        logging.debug("after_speial_rules:\n"
                      + "\tafter_special_rules[0]:\n%s\n"
                      + "\tafter_special_rules[1]:\n%s\n"
                      + "\tafter_special_rules[2]:\n%s",
                      tab_data_str(actions[0]),
                      tab_data_str(actions[1]),
                      tab_data_str(actions[2]))

    add_desktop_size = 9 - len(actions[1])

    desktop_sizes = math.floor(add_desktop_size/len(actions[0]))
    additional_desktops = max(add_desktop_size - (desktop_sizes*len(actions[0])), 0)

    for row in sorted(actions[0], key=lambda x: (int(x.get('xoffset', 4096)), int(x.get('yoffset', 128))), reverse=False):
        stolen_desktop = 0
        if additional_desktops > 0:
            stolen_desktop = 1
            additional_desktops = additional_desktops - 1

        action_cmd = ['bspc', 'monitor', row[BSPC_KEY], '-n', str(monitor_id), '-d', *["{}/{}".format(monitor_id, string.ascii_letters[i]) for i in range(desktop_sizes + stolen_desktop)]]

        if debug_on:
            action_cmd.insert(0, 'echo')
        else:
            logging.info("Adding monitor {} with bspc id {}".format(row[NAME_KEY], row[BSPC_KEY]))
        debug_overridden_execute_command(action_cmd)
        monitor_id = 1 + monitor_id

    for row in sorted(actions[1], key=lambda x: (int(x.get('xoffset', 4096)), int(x.get('yoffset', 128))), reverse=False):

        action_cmd = ['bspc', 'monitor', row[BSPC_KEY], '-n', str(monitor_id), '-d', '{}/a'.format(monitor_id)]

        if debug_on:
            action_cmd.insert(0, 'echo')
        else:
            logging.info("Chilling monitor {} with bspc id {}".format(row[NAME_KEY], row[BSPC_KEY]))
        debug_overridden_execute_command(action_cmd)
        monitor_id = 1 + monitor_id

    for row in actions[2]:
        action_cmd = ['bspc', 'monitor', row[BSPC_KEY], '-r']
        if debug_on:
            action_cmd.insert(0, 'echo')
        else:
            logging.info("Removing monitor {} with bspc id {}".format(row[NAME_KEY], row[BSPC_KEY]))
        debug_overridden_execute_command(action_cmd)

    correct_order = [x[BSPC_KEY] for x in sorted(actions[0], key=lambda x: (int(x['xoffset']), int(x['yoffset'])), reverse=False)] + [x[BSPC_KEY] for x in actions[1]]
    if debug_on:
        logging.debug("Trying to get correct order:\n"
                      + "\tcorrect_order:\n%s\n"
                      + "\tactions[0]:\n%s\n"
                      + "\tactions[1]:\n%s",
                      tab_data_str(correct_order),
                      tab_data_str(actions[0]),
                      tab_data_str(actions[1]))

    result = subprocess.run(['bspc', 'query', '-M'], stdout=subprocess.PIPE)
    monitors = result.stdout.decode('utf-8').split()

    swapped = set()
    for monitor in zip(correct_order, monitors):
        if monitor[0] != monitor[1] and not (monitor[0] in swapped or monitor[1] in swapped):
            action_cmd = ['bspc', 'monitor', monitor[1], '-s', monitor[0]]
            if debug_on:
                action_cmd.insert(0, 'echo')
            swapped.add(monitor[0])
            debug_overridden_execute_command(action_cmd)
    result = subprocess.run(['bspc', 'query', '-M'], stdout=subprocess.PIPE)
    monitors = result.stdout.decode('utf-8').split()


def print_autorandr_fingerprint() -> None:
    result = subprocess.run(['autorandr', '--fingerprint'], stdout=subprocess.PIPE)
    fingerprints = result.stdout.decode('utf-8')
    logging.debug("autorandr fingerprint outputted: %s", fingerprints)


def filter_monitors_without_bspc_id(xrandr_results: Monitors) -> Monitors:
    return [x for x in xrandr_results if BSPC_KEY in x]


def change_bspc_monitors_settings(state: bool) -> None:
    state_text = 'true' if state else 'false'

    if state:
        to_add, _, _ = get_monitors_actions()
        if len(to_add) == 0:
            logging.warning("Trying to enable remove monitors settings before any display exists")
            print_autorandr_fingerprint()
            return

    debug_overridden_execute_command(['/usr/bin/bspc', 'config', 'remove_disabled_monitors', state_text])
    debug_overridden_execute_command(['/usr/bin/bspc', 'config', 'remove_unplugged_monitors', state_text])


def check_lid_closed(monitor_name: str) -> bool:
    if not re.match(r'(eDP(-?[0-9]\+)*|LVDS(-?[0-9]\+)*)', monitor_name):
        logging.debug('is lid closed %s: False', monitor_name)

        return False

    lid_state_file = '/proc/acpi/button/lid/LID0/state'

    if not os.path.exists(lid_state_file):
        return False

    with open(lid_state_file, 'r') as f:
        lid_status = f.read().strip()
        is_closed = 'closed' in (x.strip() for x in lid_status.split(':'))
        logging.debug('is lid closed %s: %s', monitor_name, repr(is_closed))
        return is_closed


def check_monitors(xrandr_data):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser_group = parser.add_mutually_exclusive_group()
    parser_group.add_argument('--bspc-remove-monitors', choices=['true', 'false'], dest='remove_monitors')
    parser_group.add_argument('--debug', action='store_true')

    args = parser.parse_args()

    if args.debug:
        loggingLevel = logging.DEBUG
        logging.basicConfig(level=loggingLevel,
                            format='%(asctime)s %(levelname)-8s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
    else:
        loggingLevel = logging.INFO
        logging.basicConfig(filename="/var/tmp/fix_display.log",
                            level=loggingLevel,
                            format='%(asctime)s %(levelname)-8s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    if args.debug:
        found_randrids = get_monitors_from_bspc()

        logging.debug('get_monitors_from_xrandr length: %s', str(len(get_monitors_from_xrandr(found_randrids))))

        logging.debug('lid closed: %s', str(check_lid_closed("eDP1")))
        __debug_is_on = True
        actions = get_monitors_actions()

        if not len(actions[0]) == 0:
            execute_bspc_commands(actions)

    elif args.remove_monitors:
        logging.info("Changing remove monitors settings to %s", args.remove_monitors)
        remove_choice = args.remove_monitors == 'true'
        change_bspc_monitors_settings(remove_choice)
        exit()

    else:
        logging.info("Removing and adding monitors.")

        actions = get_monitors_actions()
        logging.debug('get_monitors_actions: actions (length: %d): %s', len(actions), repr(actions))

        if actions and not len(actions[0]) == 0:
            execute_bspc_commands(actions)
        else:
            logging.warning("No monitor available!")
        exit()
