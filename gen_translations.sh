#!/bin/sh

usage() {
cat << EOF
usage: $0 -a [DIR]
usage: $0 <ADDON_DIR> <OUTPUT_FILE>

OPTIONS:
   -a [DIR]  export the .pot files for all web addons found
             at target path (default: ./addons) 
   -h        print this message
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
    if [ "x$(which msgcat)" = "x" ]
    then
        echo "The msgcat command from the gettext tools is required in the PATH."
        echo "On a Debian/Ubuntu system you may install gettext via 'sudo apt-get install gettext'"
        exit 1
    fi

    echo "Extracting all web addons translations"
    executable=$0
    target_dir=${1:-./addons}
    echo "Using target dir: ${target_dir}"
    for mod in $(find ${target_dir} -type d -name 'static' -exec sh -c 'basename $(dirname {})' \;); do
       echo ${mod}
       mod_pot=${target_dir}/${mod}/i18n/${mod}.pot
       web_pot=${mod_pot}.web
       mkdir -p $(dirname ${web_pot})
       $executable ${target_dir}/${mod} ${web_pot} 
       if [ -f "${mod_pot}" ]; then
         echo "Merging with existing PO file: ${mod_pot}"
         msgcat --force-po -o "${mod_pot}.tmp" ${mod_pot} ${web_pot}
         mv ${mod_pot}.tmp ${mod_pot}
         rm ${web_pot}
       else
         echo "Renaming to final PO file: ${mod_pot}"
         mv ${web_pot} ${mod_pot}
       fi
    done
elif [ -n "$2" ]
then
    ./npybabel.py extract -F babel.cfg -o $2 -k _t -k _lt --no-default-keywords $1
else
    usage
fi
