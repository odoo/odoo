IMAGE = ghcr.io/mohammedj-sadiq/kswco-odoo

PROD_DB_USER ?= odoo
PROD_DB_NAME ?= KSWCO

.PHONY: dev dev-build dev-down prod-build prod-push prod-up prod-down logs prod-logs dev-db-pull

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f odoo

prod-build:
	docker build -t $(IMAGE):latest .

prod-push:
	docker push $(IMAGE):latest

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f odoo

# Refresh dev database from local production (KSWCO → odoo_dev). Never touches prod.
# Production Postgres is on this same machine, accessed via Unix socket (peer auth).
dev-db-pull:
	@echo "Stopping Odoo..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml stop odoo
	@echo "Dumping $(PROD_DB_NAME) via local socket..."
	pg_dump -U $(PROD_DB_USER) -d $(PROD_DB_NAME) --no-owner --no-acl -f /tmp/prod_dump.sql
	@echo "Recreating odoo_dev..."
	docker exec odoo-db-1 psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo_dev;"
	docker exec odoo-db-1 psql -U odoo -d postgres -c "CREATE DATABASE odoo_dev OWNER odoo;"
	@echo "Restoring into dev container..."
	tar -cf - -C /tmp prod_dump.sql | docker cp - odoo-db-1:/tmp/
	docker exec odoo-db-1 psql -U odoo -d odoo_dev -f /tmp/prod_dump.sql -q
	rm /tmp/prod_dump.sql
	@echo "Starting Odoo..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml start odoo
	@echo "Done — dev database is now a fresh copy of $(PROD_DB_NAME)."
