#!/bin/sh

set -e

ODOO_LIB_DIR=/var/lib/odoo
ODOO_USER="odoo"
ODOO_GROUP="odoo"
GSFONTS_DIR=/usr/share/fonts/type1/gsfonts

case "${1}" in
    remove)
        deluser --quiet --system $ODOO_USER || true
        delgroup --quiet --system --only-if-empty $ODOO_GROUP || true
        	# remove workaround for https://bugs.debian.org/1059326
        if [ -L ${GSFONTS_DIR}/n021003l.pfb ] ; then
            rm ${GSFONTS_DIR}/n021003l.pfb
            if [ "$(ls -A ${GSFONTS_DIR})" = ".created-by-odoo-package" ] ; then
                rm -fr ${GSFONTS_DIR}
            fi
    	fi
        ;;

    purge)
        if [ -d "$ODOO_LIB_DIR" ]; then
            rm -rf $ODOO_LIB_DIR
        fi
        ;;

    upgrade|failed-upgrade|abort-install|abort-upgrade|disappear)
        ;;

esac

#DEBHELPER#

exit 0
