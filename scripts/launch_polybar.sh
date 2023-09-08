#!/bin/sh
(
flock 200
#found_polybar="$(pgrep -x polybar)"
current_uid=$(id -u)

killall -q polybar

# Wait until the processes have been shut down
while pgrep -u "$current_uid" -x polybar > /dev/null; do sleep 1; done

#if [ -z "$(pgrep -x polybar)" ]; then
#
#fi

IFS=$(echo -en "\n\b")

PRIMARY_MONITOR="eDP1"

for m in $(polybar --list-monitors); do
#  echo "start"
  if [[ $m == *"primary"* ]]; then
    PRIMARY_MONITOR=$(echo $m | cut -d":" -f1)
    #echo "$m"
  fi
  #echo "fudge"
done

printf "Primary monitor is: %s" $PRIMARY_MONITOR

for m in $(polybar --list-monitors | cut -d":" -f1); do
  export MONITOR=$m
  export TRAY_POSITION="none"
  if [ $m == $PRIMARY_MONITOR ]; then
    TRAY_POSITION="right"
  fi
  #if [ -z "$found_polybar" ]; then
    polybar --reload main </dev/null > /var/tmp/polybar-$m.log 2>&1 200>&- &
  #else
  #  polybar-msg cmd restart
  #fi
  disown
  sleep 1
done

#else
#    polybar-msg cmd restart
#fi
) 200>/var/tmp/polybar-launch.lock
