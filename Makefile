# -*- makefile -*-

addons-path := bin/addons/ 
root-path := bin/  
port := 8069
net_port := 8070 
interrogation_file := bin/addons/base_quality_interrogation.py
login := admin
password := admin

openerp-test:	
	python $(interrogation_file) openerp-test  --root-path=$(root-path) --addons-path=$(addons-path) --net_port=$(net_port) --port=$(port) --login=$(login) --password=$(password)

version:
	python bin/openerp-server.py --version
