#!/bin/sh

usage() {
cat << EOF
usage: $0 -a
usage: $0 DIR OUTPUT_FILE

OPTIONS:
   -a    recreate the .pot file for all addons
   -h    print this message
EOF
exit 0
}

do_all=

while getopts "a" opt
do
    case "$opt" in
    a) 
        do_all=true;;
    h)
        usage;;
    \?)
        usage;;  
  esac
done

shift $((OPTIND-1))

if [ -n "$do_all" ]
then
    echo "Extracting all the translations"
    executable=$0
    extract_module() {
       $executable addons/$1 addons/$1/po/$1.pot 
    }
    extract_module base
    extract_module base_calendar
    extract_module base_dashboard
    extract_module base_default_home
    extract_module base_diagram
    extract_module base_gantt
    extract_module base_graph
    extract_module base_hello
    extract_module web_chat
    extract_module web_mobile
elif [ -n "$2" ]
then
    ./npybabel.py extract -F babel.cfg -o $2 -k _t --no-default-keywords $1
else
    usage
fi
