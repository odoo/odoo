# -*- makefile -*-

addons-path := bin/addons/ 
root-path := bin/  
port := 8069
net_port := 8070 
module := base
database := terp
language := fr_FR
i18n-import := bin/addons/base/i18n/fr_FR.po
interrogation_file := bin/addons/quality_integration_server/base_quality_interrogation.py
login := admin
password := admin

start:        
	python $(interrogation_file) start-server --root-path=$(root-path) --addons-path=$(addons-path) --port=$(port)

create-db:
	python $(interrogation_file) create-db --database=$(database) --root-path=$(root-path) --addons-path=$(addons-path) --port=$(port) --login=$(login) --password=$(password)

drop-db:
	python $(interrogation_file) drop-db --database=$(database) --root-path=$(root-path) --addons-path=$(addons-path) --port=$(port)

install-module:	
	python $(interrogation_file) install-module --modules=$(module) --database=$(database) --root-path=$(root-path) --addons-path=$(addons-path) --port=$(port) --login=$(login) --password=$(password)

upgrade-module:	
	python $(interrogation_file) upgrade-module --modules=$(module) --database=$(database) --root-path=$(root-path) --addons-path=$(addons-path) --port=$(port) --login=$(login) --password=$(password)
	

install-translation:    
	python $(interrogation_file) install-translation --database=$(database) --translate-in=$(i18n-import) --port=$(port) --login=$(login) --password=$(password) --root-path=$(root-path) --addons-path=$(addons-path)
    

version:
	python bin/openerp-server.py --version

check-quality:	
	python $(interrogation_file) check-quality --database=$(database) --modules=$(module) --port=$(port) --login=$(login) --password=$(password) --addons-path=$(addons-path) --root-path=$(root-path)
	



