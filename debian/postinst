#!/bin/sh

set -e

ODOO_CONFIGURATION_FILE=/etc/odoo/odoo.conf
ODOO_GROUP="odoo"
ODOO_DATA_DIR=/var/lib/odoo
ODOO_LOG_DIR=/var/log/odoo
ODOO_USER="odoo"
GSFONTS_DIR=/usr/share/fonts/type1/gsfonts

case "${1}" in
    configure)
        if ! getent passwd | grep -q "^odoo:"; then
            adduser --system --home $ODOO_DATA_DIR --quiet --group $ODOO_USER
            # Data dir
            chown $ODOO_USER:$ODOO_GROUP $ODOO_DATA_DIR
        fi
        # Register "$ODOO_USER" as a postgres user with "Create DB" role attribute
        su - postgres -c "createuser -d -R -S $ODOO_USER" 2> /dev/null || true
        # Configuration file
        chown $ODOO_USER:$ODOO_GROUP $ODOO_CONFIGURATION_FILE
        chmod 0640 $ODOO_CONFIGURATION_FILE
        # Log
        mkdir -p $ODOO_LOG_DIR
        chown $ODOO_USER:$ODOO_GROUP $ODOO_LOG_DIR
        chmod 0750 $ODOO_LOG_DIR
        	# work around https://bugs.debian.org/1059326

        if ! [ -e ${GSFONTS_DIR}/n021003l.pfb ] ; then
            if ! [ -d ${GSFONTS_DIR} ] ; then
                mkdir ${GSFONTS_DIR}
                touch ${GSFONTS_DIR}/.created-by-odoo-package
            fi
            ln -s /usr/share/fonts/X11/Type1/C059-Roman.pfb ${GSFONTS_DIR}/n021003l.pfb
        fi
        ;;
    *)
        ;;
esac

#DEBHELPER#

exit 0
