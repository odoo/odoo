#!/bin/sh

set -e

ODOO_CONFIGURATION_FILE=/etc/openerp/openerp-server.conf
ODOO_CONFIGURATION_DIR=/etc/openerp
ODOO_DATA_DIR=/var/lib/openerp
ODOO_GROUP="openerp"
ODOO_LOG_DIR=/var/log/openerp
ODOO_USER="openerp"

if ! getent passwd | grep -q "^openerp:"; then
    groupadd $ODOO_GROUP
    adduser --system --no-create-home $ODOO_USER -g $ODOO_GROUP
fi
# Register "openerp" as a postgres superuser 
su - postgres -c "createuser -s openerp" 2> /dev/null || true
# Configuration file
mkdir -p $ODOO_CONFIGURATION_DIR
echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = False
db_port = False
db_user = openerp
db_password = False
addons_path = /usr/lib/python2.6/site-packages/openerp/addons
" > $ODOO_CONFIGURATION_FILE
chown $ODOO_USER:$ODOO_GROUP $ODOO_CONFIGURATION_FILE
chmod 0640 $ODOO_CONFIGURATION_FILE
# Log
mkdir -p $ODOO_LOG_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_LOG_DIR
chmod 0750 $ODOO_LOG_DIR
# Data dir
mkdir -p $ODOO_DATA_DIR
chown $ODOO_USER:$ODOO_GROUP $ODOO_DATA_DIR

echo '#!/bin/sh
### BEGIN INIT INFO
# Provides:     openerp-server
# Required-Start:   $remote_fs $syslog
# Required-Stop:    $remote_fs $syslog
# Should-Start:     $network
# Should-Stop:      $network
# Default-Start:    2 3 4 5
# Default-Stop:     0 1 6
# Short-Description:    Enterprise Resource Management software
# Description:      Open ERP is a complete ERP and CRM software.
### END INIT INFO
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin
DAEMON=/usr/bin/openerp-server
NAME=openerp-server
DESC=openerp-server
CONFIG=/etc/openerp/openerp-server.conf
LOGFILE=/var/log/openerp/openerp-server.log
USER=openerp
test -x ${DAEMON} || exit 0
set -e
do_start () {
    echo -n "Starting ${DESC}: "
    start-stop-daemon --start --quiet --pidfile /var/run/${NAME}.pid --chuid ${USER} --background --make-pidfile --exec ${DAEMON} -- --config=${CONFIG} --logfile=${LOGFILE}
    echo "${NAME}."
}
do_stop () {
    echo -n "Stopping ${DESC}: "
    start-stop-daemon --stop --quiet --pidfile /var/run/${NAME}.pid --oknodo
    echo "${NAME}."
}
case "${1}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart|force-reload)
        echo -n "Restarting ${DESC}: "
        do_stop
        sleep 1
        do_start
        ;;
    *)
        N=/etc/init.d/${NAME}
        echo "Usage: ${NAME} {start|stop|restart|force-reload}" >&2
        exit 1
        ;;
esac
exit 0
' > /etc/init.d/openerp
chmod 700 /etc/init.d/openerp
