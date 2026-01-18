# NorTK odoo

DB_NAME="odoo"
CONFIG_FILE="utils/config/odoo.conf"
VENV=odoo-venv-dev
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

./data:
	mkdir data

dirs: data

venv:
	uv python install 3.13
	uv venv --allow-existing $(VENV) --python 3.13
	$(PIP) install -r requirements.txt

db: data
	podman run -d --replace --name=odoo_pg                       \
		-e POSTGRES_PASSWORD=prueba123                           \
		-v ./data:/var/lib/postgresql/data:U,Z                   \
		-p 127.0.0.1:9432:5432 ghcr.io/enterprisedb/postgresql:17

dev: dirs db venv
	$(PYTHON) ./odoo-bin --addons-path="addons/,../tutorials" \
		--config=$(CONFIG_FILE)                     \
		-d $(DB_NAME)

clean:
	rm -rf data $(VENV)
