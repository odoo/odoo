#!/bin/bash
rm -f /home/pi/odoo/posbox.pid

foo() {
	while true
	do
		if wget --quiet localhost:8069/hw_proxy/hello -O /dev/null 
		then
			echo 'Odoo Server Available'
			sudo ./led.sh
			exit 1
		else
			echo 'Odoo Server Not Yet Reachable'
			sleep 1
		fi
	done
}

foo &

