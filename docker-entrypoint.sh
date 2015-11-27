#!/bin/bash

set -e
echo "admin_passwd = $ADMIN_PASSWORD" >> server.conf
case "$1" in
	--)
		shift
		exec openerp-server -c server.conf "$@"
		;;
	-*)
		exec openerp-server -c server.conf "$@"
		;;
	*)
		exec "$@"
esac

exit 1