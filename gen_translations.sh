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
    extract_module web
    extract_module web_calendar
    extract_module web_dashboard
    extract_module web_default_home
    extract_module web_diagram
    extract_module web_gantt
    extract_module web_graph
    extract_module web_hello
    extract_module web_chat
    extract_module web_mobile
    extract_module web_rpc
elif [ -n "$2" ]
then
    ./npybabel.py extract -F babel.cfg -o $2 -k _t --no-default-keywords $1
else
    usage
fi
