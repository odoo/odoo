#!/usr/bin/bash

""" Sample export script """

BASE=.                               # base of your multiverse
VENV=$BASE/.venv311                  # your virtual environment
ADDONS=--addons-path=odoo/addons,addons,../enterprise
SERVER_OPTS=--stop-after-init
DB_NAME=`date "+temp_%Y%m%d_%H%M%S"`
DB="-d $DB_NAME"

echo New temp database: $DB_NAME


function contextmanager() {
    pushd $BASE/odoo > /dev/null     # cd to the Odoo folder
    source $VENV/bin/activate        # Setup virtualenv
    set -v                           # Set echo on
    function cleanup {
        ./odoo-bin db drop $DB_NAME  # Drop the temp DB
        popd > /dev/null             # Back to original folder
        deactivate                   # Deactivate virtualenv
        set +v                       # Set echo off
    }
    trap cleanup EXIT                # At exit, run `cleanup`
}
contextmanager

# Install account on a new temporary db
./odoo-bin $ADDONS $DB $SERVER_OPTS -i account
# Export account
./odoo-bin $ADDONS i18n export $DB account
# Install all localization modules in community
./odoo-bin $ADDONS i18n list $DB --l10n=yes --folder=. --del=',' \
    | xargs ./odoo-bin $ADDONS $DB $SERVER_OPTS -i
# Export installed localization modules
./odoo-bin $ADDONS i18n list $DB --l10n=yes --folder=. \
    | xargs ./odoo-bin $ADDONS i18n export $DB
