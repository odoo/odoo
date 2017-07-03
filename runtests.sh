#!/bin/bash
#
# Usage: ./runtests.sh [-i addons]

# The name of the DB is built from the name of the addon but it's hashed to
# avoid clashes in a shared DB env with a CI server not running in a
# container.
NOW=`date --utc +"%Y%m%d%H%M%N"`
CDIR=`pwd`
HASH=`echo "$CDIR-$NOW" | md5sum -t - | awk '{print $1}' |cut -b-9`
VENV=/tmp/venv_"$HASH"
DB=tdb_"$HASH"
STDOUT=$(mktemp --suffix="-odoo-$HASH.log")

ADDONS=''
while [ \! -z "$1" ]; do
    case $1 in
         -i)
             shift;
             if [ -z "$1" ]; then
                 echo "-i requires an argument"
                 exit 1;
             else
                 ADDONS="$1"
             fi
             shift;;
         *)
             ARGS="$ARGS $1"
             shift;;
    esac
done


echo "Creating virtualenv $VENV and installing the packages.  Wait for it."
virtualenv --no-site-packages $VENV &&
    trap 'source deactivate; rm -rf $VENV; dropdb $DB; exit $CODE ' EXIT && \
    trap 'source deactivate; rm -rf $VENV; dropdb $DB; rm -f -- $STDOUT; exit 13' TERM INT KILL

echo "Not done yet..."
source $VENV/bin/activate
pip install -q -r requirements.txt
pip install -qe .

echo "Logs in $STDOUT"

EXECUTABLE="./openerp-server"

# Just in case
dropdb $DB 2>/dev/null

ARGS='--stop-after-init --test-enable --log-level=test --workers=0 --max-cron-threads=0'
if [ -z "$ADDONS" ]; then
    # XXX: Putting -i all does not work.  I have to look in standard addons
    # places.  However, I omit hardware-related addons.
    ADDONS=`ls addons | grep -v ^hw| xargs | tr " " ","`
    ADDONS="$ADDONS,`ls openerp/addons | xargs | tr " " ","`"
fi
ARGS="$ARGS -i $ADDONS"

echo running $EXECUTABLE -d $DB $ARGS


# Create the DB install the addons and run tests.
createdb -E UTF-8 --template=template0 "$DB" && \
    trap 'source deactivate; rm -rf $VENV; dropdb $DB; exit $CODE ' EXIT && \
    trap 'source deactivate; rm -rf $VENV; dropdb $DB; rm -f -- $STDOUT; exit 13' TERM INT KILL && \
    $EXECUTABLE -d $DB --db-filter=^$DB\$ $ARGS | tee $STDOUT

if egrep -q "(At least one test failed when loading the modules.|(ERROR|CRITICAL) $DB)" $STDOUT; then
    CODE=1
else
    CODE=0
fi

exit $CODE
