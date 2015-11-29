#!/bin/bash

set -e


echo "[options]" >> server.conf
echo "admin_passwd = $ADMIN_PASSWORD" >> server.conf
echo "xmlrpc_port = 8069" >> server.conf
echo "$AWS_S3_KEY:$AWS_S3_SECRET" >> ~/.passwd-s3fs
chmod 600 ~/.passwd-s3fs

case "$1" in
	--)
		shift
		mkdir ~/.local
		if [ ! -d "~/.local" ]; then
			mkdir ~/.local
		fi
		s3fs -o use_cache=/tmp/s3  $AWS_S3_BUCKET ~/.local 
		python2.7 /home/odoo/odoo/openerp-server -c server.conf "$@"
		;;
	-*)
		if [ ! -d "˜/.local" ]; then
			mkdir ~/.local
		fi
		s3fs -o use_cache=/tmp/s3 $AWS_S3_BUCKET ~/.local 
		python2.7 /home/odoo/odoo/openerp-server -c server.conf "$@"
		;;
	*)
		exec "$@"
esac

exit 1
