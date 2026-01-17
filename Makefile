# NorTK odoo

DB_NAME="odoo"
CONFIG_FILE="utils/config/odoo.conf"

./data:
	mkdir data

dirs: data

db: data
	podman run -d --replace --name=odoo_pg                       \
		-e POSTGRES_PASSWORD=prueba123                           \
		-v ./data:/var/lib/postgresql/data:U,Z                   \
		-p 127.0.0.1:9432:5432 ghcr.io/enterprisedb/postgresql:17

dev: dirs db
	./odoo-bin --addons-path="addons/,../tutorials" \
    	--config=${CONFIG_FILE}                     \
    	-d ${DB_NAME}

clean:
	rm -rf data
