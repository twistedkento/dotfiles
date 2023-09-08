#!/usr/bin/env bash
service=$(ykman oath accounts list | rofi -theme solarized -font "hack 10" -dmenu -no-fixed-num-lines -location 0 -i -p "Account")

if [ -n "${service}" ]; then
  code_data="$(ykman oath accounts code "${service}")"

  awk -v code_data="${code_data}" 'BEGIN { n=split(code_data, a); printf "%s",a[n] }' | xclip -selection clipboard
fi
