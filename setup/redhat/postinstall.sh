#!/bin/bash

set -e

ODOO_CONFIGURATION_DIR=/etc/odoo
ODOO_CONFIGURATION_FILE=$ODOO_CONFIGURATION_DIR/openerp-server.conf
ODOO_DATA_DIR=/var/lib/odoo
ODOO_GROUP="odoo"
ODOO_LOG_DIR=/var/log/odoo
ODOO_USER="odoo"

if ! getent passwd | grep -q "^odoo:"; then
    groupadd $ODOO_GROUP
    adduser --system --no-create-home $ODOO_USER -g $ODOO_GROUP
fi
# Register "$ODOO_USER" as a postgres superuser
su - postgres -c "createuser -s $ODOO_USER" 2> /dev/null || true
# Configuration file
mkdir -p $ODOO_CONFIGURATION_DIR
# can't copy debian config-file as addons_path is not the same
echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = False
db_port = False
db_user = $ODOO_USER
db_password = False
addons_path = /usr/local/lib/python2.7/dist-packages/openerp/addons
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

INIT_FILE=/etc/init.d/openerp
touch $INIT_FILE
chmod 0700 $INIT_FILE
# FIXME this is a copy of debian/init file.
#       If anyone know how to tell bdist_rpm to use this file directly...
cat << 'EOF' > $INIT_FILE
#!/bin/bash
### BEGIN INIT INFO
# Provides:          openerp-server
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start openerp daemon at boot time
# Description:       Enable service provided by daemon.
# X-Interactive:     true
### END INIT INFO
## more info: http://wiki.debian.org/LSBInitScripts

PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin
DAEMON=/usr/bin/openerp-server
NAME=openerp
DESC=openerp
CONFIG=/etc/odoo/openerp-server.conf
LOGFILE=/var/log/odoo/openerp-server.log
PIDFILE=/var/run/${NAME}.pid
USER=odoo
export LOGNAME=$USER

test -x $DAEMON || exit 0
set -e

function _start() {
    start-stop-daemon --start --quiet --pidfile $PIDFILE --chuid $USER:$USER --background --make-pidfile --exec $DAEMON -- --config $CONFIG --logfile $LOGFILE
}

function _stop() {
    start-stop-daemon --stop --quiet --pidfile $PIDFILE --oknodo --retry 3
    rm -f $PIDFILE
}

function _status() {
    start-stop-daemon --status --quiet --pidfile $PIDFILE
    return $?
}


case "$1" in
        start)
                echo -n "Starting $DESC: "
                _start
                echo "ok"
                ;;
        stop)
                echo -n "Stopping $DESC: "
                _stop
                echo "ok"
                ;;
        restart|force-reload)
                echo -n "Restarting $DESC: "
                _stop
                sleep 1
                _start
                echo "ok"
                ;;
        status)
                echo -n "Status of $DESC: "
                _status && echo "running" || echo "stopped"
                ;;
        *)
                N=/etc/init.d/$NAME
                echo "Usage: $N {start|stop|restart|force-reload|status}" >&2
                exit 1
                ;;
esac

exit 0
EOF
