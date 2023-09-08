#!/usr/bin/env python3
import os.path
import shutil
import subprocess
import logging
import argparse
import re
import random
import shlex
import pathlib
import tempfile
import sqlite3

from functools import lru_cache


ID_KEY = "id"
NAME_KEY = "name"
X_KEY = "x"
Y_KEY = "y"
WIDTH_KEY = "w"
HEIGHT_KEY = "h"

aspects_cache: dict[str, dict[str, int | float | pathlib.Path]] | None = None


def get_monitors() -> list[dict[str, str | int]]:
    result = subprocess.run(['xrandr', '--listactivemonitors'], stdout=subprocess.PIPE)
    xrandr_output = result.stdout.decode('utf-8')

    monitor_pattern = re.compile(r"^\s?(?P<id>\d+):\s+"
                                 + r"(?P<randr_information>\S*)\s+"
                                 + r"(?P<w>\d+)/\d+x(?P<h>\d+)/\d+(?P<x>[+-]\d+)(?P<y>[+-]\d+)\s+"
                                 + r"(?P<name>\S*)$", re.M)
    monitor_match = monitor_pattern.finditer(xrandr_output)
    monitors = list()
    for x in monitor_match:
        logging.debug('get_monitors: found monitor %s', x.groupdict())
        monitors.append(x.groupdict())
    for m in monitors:
        m[X_KEY] = int(m[X_KEY])
        m[Y_KEY] = int(m[Y_KEY])
        m[WIDTH_KEY] = int(m[WIDTH_KEY])
        m[HEIGHT_KEY] = int(m[HEIGHT_KEY])
        m[ID_KEY] = int(m[ID_KEY])
    if len(monitors) == 0:
        logging.debug('get_monitors: found no active monitors')

    return monitors


def is_inside_other_monitor(monitor: dict[str, str | int], monitors: list[dict[str, int | str]]) -> bool:
    for other_monitor in monitors:
        if monitor[ID_KEY] == other_monitor[ID_KEY]:
            continue
        inside_x = (int(monitor[X_KEY]) >= int(other_monitor[X_KEY]) and int(monitor[WIDTH_KEY]) + int(
            monitor[X_KEY]) <= int(other_monitor[WIDTH_KEY]) + int(other_monitor[X_KEY]))
        inside_y = (int(monitor[Y_KEY]) >= int(other_monitor[Y_KEY]) and int(monitor[HEIGHT_KEY]) + int(
            monitor[Y_KEY]) <= int(other_monitor[HEIGHT_KEY]) + int(other_monitor[Y_KEY]))
        if inside_x and inside_y:
            return True
    return False


def get_size_of_xscreen(monitors: list[dict[str, str | int]]) -> dict[str, int]:
    size = dict()
    size[WIDTH_KEY] = max((int(m[X_KEY]) + int(m[WIDTH_KEY]) for m in monitors))
    size[HEIGHT_KEY] = max((int(m[Y_KEY]) + int(m[HEIGHT_KEY]) for m in monitors))
    return size


@lru_cache
def get_images(folder: pathlib.Path) -> list[pathlib.Path]:
    bg_papers: list[pathlib.Path] = list()
    types = ('png', 'jpg', 'jpeg', 'webp')

    for t in types:
        bg_papers.extend(folder.glob(f'**/*.{t}'))

    if len(bg_papers) == 0:
        raise Exception(f'get_images: no images found in folder {folder}')

    logging.debug('get_images: found %s images in folder %s', len(bg_papers), folder)

    return bg_papers


def match_almost(monitor_aspect_ratio: float, image_aspect_ratio: float) -> bool:
    return abs(monitor_aspect_ratio - image_aspect_ratio) <= 0.2


def get_image_file_special(folder: pathlib.Path, monitor: dict[str, str | int]) -> pathlib.Path:
    files = get_aspects(get_images(folder))

    aspect_ratio = round(int(monitor[WIDTH_KEY])/int(monitor[HEIGHT_KEY]), 1)
    logging.debug("get_image_file_special: Monitor aspect_ratio %f", aspect_ratio)

    # found_correct = [files[x]['path'] for x in files if files[x]['aspect_ratio'] == aspect_ratio]
    found_correct = [files[x]['path'] for x in files if match_almost(files[x]['aspect_ratio'], aspect_ratio)]
    logging.debug("get_image_file_special: found correct aspect_ratio %s", ','.join([str(x) for x in found_correct]))

    if len(found_correct) == 0:
        # fallback for when no images are found
        found_correct = [files[x]['path'] for x in files]

    return random.choice(found_correct)


def get_image_file(folder: pathlib.Path) -> pathlib.Path:
    images = get_images(folder)
    return random.choice(images)


def load_db_images():
    image_sizes = dict()

    global con
    cur = con.cursor()
    for row in cur.execute("SELECT * FROM images;"):
        loaded_file = pathlib.Path(row['path'])
        if not os.path.exists(loaded_file):
            print(f'FUCK! {loaded_file.absolute().__str__()} exists in db but not in FS')
            continue
        image_sizes[loaded_file.absolute().__str__()] = {'path': loaded_file.absolute(), WIDTH_KEY: row['width'], HEIGHT_KEY: row['height'], 'aspect_ratio': row['ratio'], 'size': row['size'], 'modified': row['modified']}
    return image_sizes


def get_aspects(files: list[pathlib.Path]):
    global aspects_cache

    if aspects_cache:
        return aspects_cache
    image_sizes = load_db_images()

    for f in files:
        if f.absolute().__str__() in image_sizes:
            filestat = f.absolute().lstat()
            row_key = f.absolute().__str__()
            image = image_sizes[row_key]

            if image['size'] == filestat.st_size and image['modified'] == filestat.st_mtime_ns:
                print(f'CACHED: {f.absolute()} is in images_sizes')
                continue

            image_sizes.pop(row_key)

            with con:
                con.execute('DELETE FROM images WHERE path=?;', (row_key,))
        print(f'MISSING {f.absolute()} is NOT in images_sizes')
        result = subprocess.run(['identify', '-ping', '-format', '\'%w %h\'', f.absolute()], stdout=subprocess.PIPE)
        identify_output = result.stdout.decode('utf-8')

        size_pattern = re.compile(r"(?P<w>\d+)\s+(?P<h>\d+)")
        image_size = size_pattern.search(identify_output)
        if image_size:
            image_data = image_size.groupdict()
            # print(image_data['width'])
            # print(image_data['height'])
            # print(f.absolute().name)
            filestat = f.absolute().lstat()

            with con:
                new_row = (f.absolute().__str__(),
                           int(image_data[WIDTH_KEY]),
                           int(image_data[HEIGHT_KEY]),
                           round((float(image_data[WIDTH_KEY])/float(image_data[HEIGHT_KEY])), 1),
                           filestat.st_size,
                           filestat.st_mtime_ns)

                con.execute('INSERT INTO images(path, width, height, ratio, size, modified) VALUES(?,?,?,?,?,?)', new_row)

            image_sizes[f.absolute().name] = {
                    'path': f,
                    WIDTH_KEY: int(image_data[WIDTH_KEY]),
                    HEIGHT_KEY: int(image_data[HEIGHT_KEY]),
                    'aspect_ratio': round(int(image_data[WIDTH_KEY])/int(image_data[HEIGHT_KEY]), 1),
                    'size': filestat.st_size,
                    'modified': filestat.st_mtime_ns,
                }

    # __import__('pprint').pprint(image_sizes)

    aspects_cache = image_sizes
    return image_sizes


def generate_wallpaper(arguments: argparse.Namespace) -> None:
    monitors = get_monitors()
    if len(monitors) == 0:
        raise Exception("empty monitor list")
    filtered_monitors = list()
    for monitor in monitors:
        if is_inside_other_monitor(monitor, monitors):
            logging.debug('generate_wallpaper: is inside other monitor = %s', monitor)
            continue
        filtered_monitors.append(monitor)
    logging.debug('generate_wallpaper: to get backgrounds = %s', filtered_monitors)
    xscreen_size = get_size_of_xscreen(filtered_monitors)

    cmd_start = f'magick -size {xscreen_size[WIDTH_KEY]}x{xscreen_size[HEIGHT_KEY]} canvas:black'
    screen_part = ' '.join((
                           f'\'{get_image_file_special(arguments.folder, m).absolute()}\' -geometry {m[WIDTH_KEY]}x{m[HEIGHT_KEY]}{int(m[X_KEY]):+d}{int(m[Y_KEY]):+d}\\! -composite'
                           for m in filtered_monitors))

    cmd_text = f'{cmd_start} {screen_part} {arguments.temp_file}'
    logging.debug('generate_wallpaper: running command = %s', cmd_text)
    imagemagick_cmd = shlex.split(cmd_text)

    subprocess.run(imagemagick_cmd)


def change_wallpaper(arguments: argparse.Namespace) -> None:
    logging.debug('change_wallpaper: changing wallpaper to %s', arguments.temp_file)
    subprocess.run(['feh', '--no-xinerama', '--bg-fill', arguments.temp_file])


def main(arguments: argparse.Namespace) -> None:
    tempdir = None
    try:
        if not arguments.temp_file:
            tempdir = tempfile.mkdtemp(prefix='fix_wallpaper-')
            logging.debug("main: temporary filepath not set creating temporary directory %s", tempdir)
            arguments.temp_file = pathlib.Path(tempdir, 'wallpaper.png')
        if arguments.temp_file.exists():
            logging.warning("main: temporary file already exists %s", arguments.temp_file)
        generate_wallpaper(arguments)
        change_wallpaper(arguments)
    finally:
        if tempdir is not None:
            logging.debug("main: removing temporary directory %s", tempdir)
            shutil.rmtree(tempdir)


if __name__ == '__main__':
    global con
    con = sqlite3.connect('/home/kento/scripts/images.db')
    con.row_factory = sqlite3.Row
    try:
        parser = argparse.ArgumentParser()
        parser_group = parser.add_mutually_exclusive_group()
        parser_group.add_argument('--debug', action='store_true')
        parser.add_argument('--testing', action='store_true')
        parser.add_argument('--folder', type=pathlib.Path, default='/home/kento/wallpapers/approved/')
        parser.add_argument('--temp-file', type=pathlib.Path,
                            help='filename of the wallpaper file to be created')
        args = parser.parse_args()

        if args.debug:
            loggingLevel = logging.DEBUG
            logging.basicConfig(level=loggingLevel,
                                format='%(asctime)s %(levelname)-8s: %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')
        else:
            loggingLevel = logging.INFO
            logging.basicConfig(filename="/var/tmp/fix_wallpaper.log",
                                level=loggingLevel,
                                format='%(asctime)s %(levelname)-8s: %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')

        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS images(path TEXT PRIMARY KEY, width INTEGER, height INTEGER, ratio REAL, size INTEGER, modified INTEGER)")
        con.commit()
        if args.testing:
            get_aspects(get_images(args.folder))
        else:
            main(args)
    finally:
        con.close()
    exit()
