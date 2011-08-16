#!/bin/sh

usage()
{
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
    $0  addons/base/static/src/ addons/base/po/base.pot    
elif [ -n "$2" ]
then
    ./npybabel.py extract -F babel.cfg -o $2 -k _t --no-default-keywords $1
else
    usage
fi
