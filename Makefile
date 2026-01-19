# NorTK odoo

DB_USER="odoo"
DB_NAME="odoo"
DB_PASSWORD="prueba123"
DB_CONTAINER="odoo_pg"
CONFIG_FILE="utils/config/odoo.conf.dev"
VENV_NAME=odoo-venv-dev
PYTHON=$(VENV_NAME)/bin/python

./data:
	mkdir data

dirs: data

venv:
	@echo "Setting up Python virtual environment"
	uv python install 3.13
	uv venv --allow-existing $(VENV_NAME) --python 3.13
	uv pip install -p $(VENV_NAME) -r requirements.txt

db: data
	@echo "Starting development database container"
	podman run -d --replace --name=$(DB_CONTAINER)                   \
		-e POSTGRES_PASSWORD=$(DB_PASSWORD)                          \
		-e POSTGRES_USER=$(DB_USER)                                  \
		-e POSTGRES_DB=$(DB_NAME)                                    \
		-e POSTGRES_INITDB_ARGS="--encoding UTF-8"                   \
		-v ./data:/var/lib/postgresql/data:U,Z                       \
		-p 127.0.0.1:9432:5432 ghcr.io/enterprisedb/postgresql:17 && \
		sleep $(SLEEP)

stop-db:
	podman stop $(DB_CONTAINER)

dev: dirs db venv
	@echo "Running NorTK odoo"
	$(PYTHON) ./odoo-bin --addons-path="addons/" \
		--config=$(CONFIG_FILE)                  \
		-i base                                  \
		-i web                                   \
		-i nortk_theme                           \
		-d $(DB_NAME)

clean-venv:
	@echo "Removing python virtual environment"
	rm -rf $(VENV)

clean-data:
	@echo "Warning! Removing data directory"
	sudo rm -rf data

clean: clean-venv stop-db clean-data
