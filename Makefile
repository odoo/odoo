SHELL := /bin/bash

ENV_FILE ?= $(if $(wildcard .env),.env,$(if $(wildcard .env.make),.env.make,.env))
-include $(ENV_FILE)
.EXPORT_ALL_VARIABLES:

# Context defaults for local Linux/WSL and deploy stack.
HOSTNAME_SHORT ?= $(shell hostname -s 2>/dev/null || hostname 2>/dev/null || echo unknown)
HOST_ROLE ?= $(if $(filter srv-01,$(HOSTNAME_SHORT)),srv01,$(if $(filter dex-00,$(HOSTNAME_SHORT)),dex00,$(if $(filter dex-01,$(HOSTNAME_SHORT)),dex01,unknown)))
ORIGINAL_MAKE_GOALS ?= $(MAKECMDGOALS)
OPERATIONS_DOC ?= doc/OPERATIONS_WORKFLOWS.md
ENV_FILE_OPT := $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)
COMPOSE ?= docker compose $(ENV_FILE_OPT)
PYTHON_CANDIDATES := $(wildcard .venv/bin/python3 .venv/bin/python venv/bin/python3 venv/bin/python)
PYTHON ?= $(if $(PYTHON_CANDIDATES),$(firstword $(PYTHON_CANDIDATES)),python3)
ODOO_BIN ?= ./odoo-bin
LOG_PATH ?= logs/odoo-lnav.log
PID_FILE ?= logs/odoo-manager.pid
DOMAIN ?= kodoo.online
PROD_RUNTIME ?= auto
EMAIL ?= [EMAIL_ADDRESS]
OLLAMA_MODEL ?= qwen3.5:0.8b
CLOUDFLARED_TOKEN ?=
SMOKE_PUBLIC ?= 1
MOBILE_DIR ?= mobile/kodoo-capacitor
TUI_PYTHON ?= python3
TUI_VENV ?= .venv-tui
TUI_REQUIREMENTS ?= requirements-tui.txt
TUI_REFRESH_SECONDS ?= 3
TUI_LOG_LINES ?= 20
GO ?= go
KODOO_TUI_DIR ?= kodoo-tui
KODOO_TUI_BIN ?= $(KODOO_TUI_DIR)/bin/kodoo-tui
WEBSOCKET_TEST_KEY ?= dGhlIHNhbXBsZSBub25jZQ==
PUBLIC_HTTP_PORT ?= 80
PUBLIC_HTTPS_PORT ?= 443
LOCAL_BIND_HOST ?= 127.0.0.1
LOCAL_HTTP_PORT ?= 8069
HTTP_PORT ?= $(DEV_HOST_HTTP_PORT)
INSECURE_HTTP_PORT ?= 8069
INSECURE_EVENTED_PORT ?= 8072
STOP_PORTS ?= $(PUBLIC_HTTP_PORT) $(PUBLIC_HTTPS_PORT) $(LOCAL_HTTP_PORT) $(INSECURE_EVENTED_PORT)
PROD_CONFIG ?= deploy/odoo/kodoo.prod.local.conf
PROD_CONFIG_EXAMPLE ?= deploy/odoo/kodoo.prod.conf.example
PROD_DB_NAME ?= kodoo
PROD_DB_USER ?= kodoo
PROD_DB_PASSWORD ?=
PROD_ADMIN_PASSWORD ?=
DB ?= $(PROD_DB_NAME)
TENANT_PROFILE ?= standard
TENANT_BOOTSTRAP_MODULES ?=
TENANT_PORTAL_MODULES ?= base,web,mail,portal,auth_signup,website
TENANT_STANDARD_MODULES ?= $(TENANT_PORTAL_MODULES)
TENANT_KNOWLEDGE_MODULES ?= $(TENANT_PORTAL_MODULES),document_page,document_knowledge
TENANT_GOV_MODULES ?= $(TENANT_PORTAL_MODULES),gov_suite
TENANT_SMOKE_PUBLIC ?= 1
TENANT_DEFAULT_LANG ?= pt_BR
TENANT_DEFAULT_CURRENCY ?= BRL
TENANT_COMPANY_NAME ?=
TENANT_ADMIN_LOGIN ?=
TENANT_ADMIN_PASSWORD ?=
TENANT_ADMIN_NAME ?=
TENANT_OWNER_LOGIN ?=
TENANT_OWNER_PASSWORD ?=
TENANT_OWNER_NAME ?=
TENANT_CLIENT_LOGIN ?=
TENANT_CLIENT_PASSWORD ?=
TENANT_CLIENT_NAME ?=
DEV_HOST_CONFIG ?= deploy/odoo/kodoo.dev-host.local.conf
DEV_HOST_CONFIG_EXAMPLE ?= deploy/odoo/kodoo.dev-host.conf.example
DEV_HOST_DB ?= kodoo
DEV_HOST_TEST_DB ?= ktest
DEV_HOST_HTTP_PORT ?= 8070
DEV_HOST_LOG_PATH ?= logs/odoo-dev-host.log
DEV_HOST_PID_FILE ?= logs/odoo-dev-host.pid
DEV_HOST_ADMIN_PASSWORD ?=
DEV_PROJECT_CONFIG ?= deploy/odoo/kodoo.dev-project.local.conf
DEV_PROJECT_CONFIG_EXAMPLE ?= deploy/odoo/kodoo.dev-project.conf.example
DEV_PROJECT_DB ?= ktest
DEV_PROJECT_HTTP_PORT ?= 8071
DEV_PROJECT_LOG_PATH ?= logs/odoo-dev-project.log
DEV_PROJECT_PID_FILE ?= logs/odoo-dev-project.pid
DEV_PROJECT_ADMIN_PASSWORD ?=
DEV_UPGRADE_DB ?= $(DEV_HOST_TEST_DB)
DEV_MODULES ?= gov_compras
DOCKER_DB_BIND_HOST ?= 127.0.0.1
DOCKER_DB_HOST_PORT ?= 5433
PG_LOCAL_SERVICE ?= postgresql
PG_LOCAL_SUPERUSER ?= postgres
PG_LOCAL_HOST ?= 127.0.0.1
PG_LOCAL_PORT ?= 5432
PG_LOCAL_USER ?= kodoo
PG_LOCAL_PASSWORD ?=
BACKUP_DIR ?= backups/postgres
CONFIG ?= $(DEV_HOST_CONFIG)
DB_SETUP ?= none
PRECREATE_DB ?= 0
PREBOOT_TEST_DB ?= $(DEV_HOST_TEST_DB)
COMPOSE_LOCAL := $(COMPOSE) -f docker-compose.yml -f deploy/local/docker-compose.local.yml
COMPOSE_BASE := $(COMPOSE) -f docker-compose.yml -f docker-compose.base.yml
COMPOSE_INSECURE := $(COMPOSE) -f docker-compose.yml -f deploy/insecure/docker-compose.insecure.yml
COMPOSE_GPU := $(COMPOSE) -f docker-compose.yml -f deploy/ollama/docker-compose.gpu.yml
COMPOSE_TUNNEL := $(COMPOSE) -f docker-compose.yml -f deploy/cloudflare/docker-compose.tunnel.yml -f deploy/cloudflare/docker-compose.cloudflare.yml
COMPOSE_LEAN_TUNNEL := $(COMPOSE) -f docker-compose.yml -f deploy/cloudflare/docker-compose.tunnel.yml -f deploy/cloudflare/docker-compose.cloudflare.yml -f deploy/lean-tunnel/docker-compose.lean.yml
COMPOSE_PROJECT_DB := $(COMPOSE) -f docker-compose.yml -f deploy/dev-project/docker-compose.db-only.yml
ACTIVE_PROD_RUNTIME := $(if $(filter auto,$(PROD_RUNTIME)),$(if $(strip $(CLOUDFLARED_TOKEN)),tunnel,public),$(PROD_RUNTIME))
PROD_RUNTIME_COMPOSE := $(if $(filter tunnel,$(ACTIVE_PROD_RUNTIME)),$(COMPOSE_TUNNEL),$(if $(filter local,$(ACTIVE_PROD_RUNTIME)),$(COMPOSE_LOCAL),$(COMPOSE)))
PROD_LOCAL_HTTP_ORIGIN := $(if $(filter tunnel local,$(ACTIVE_PROD_RUNTIME)),http://$(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT),http://127.0.0.1:$(PUBLIC_HTTP_PORT))
CONFIG_FIND_CMD = find . \
	\( -path './.git' -o -path './.venv' -o -path './venv' -o -path './node_modules' \) -prune -o \
	-type f \( -name '*.conf' -o -name '*.env' -o -name '*.env.*' -o -name '.env' -o -name '.env.*' \) -print | \
	LC_ALL=C sort | sed 's|^\./||'

.PHONY: help doctor deps-install clean clean-all \
	context-status host-role-status guard-dev-host guard-prod-host \
	ops-status ops-patch ops-release ops-hotfix ops-experiment ops-rollback \
	odoo-lnav build build-base up up-base up-cpu up-gpu down down-base logs logs-base status status-base \
	probe certbot certbot-renew \
	db-init db-check db-list db-manager prod-db-create prod-db-init prod-db-ensure \
	tenant-provision tenant-install-modules tenant-check tenant-smoke tenant-bootstrap-defaults tenant-adjust tenant-reset tenant-user-list tenant-user-password tenant-user-role tenant-user-create-portal tenant-user-create-client tenant-user-create-operator root-smoke \
	stop ports-clean \
	refresh-safe safe-refresh \
	env-init config-list config-view config-view-all config-edit config-create prod-config \
	odoo-start odoo-manager odoo-stop odoo-status \
	dev-host-config dev dev-stop dev-logs dev-status \
	dev-safe dev-safe-stop dev-safe-logs dev-safe-status \
	up-home down-home logs-home smoke-home troubleshoot-home \
	up-cowork down-cowork logs-cowork smoke-cowork troubleshoot-cowork \
	up-dev down-dev logs-dev smoke-dev troubleshoot-dev \
	up-project down-project logs-project smoke-project troubleshoot-project \
	tui tui-live tui-build tui-install tui-menu tui-doctor \
	odoo-tui odoo-shell odoo-fix-url \
	dev-host-db-setup dev-host-db-init dev-host-test-init \
	dev-host-up dev-host-stop dev-host-logs dev-host-status dev-host-upgrade \
	dev-project dev-project-config dev-project-db-setup dev-project-db-init \
	dev-project-up dev-project-stop dev-project-logs dev-project-status \
	dev-host-backup dev-host-restore-ktest \
	assets-rebuild \
	smoke troubleshoot up-smoke \
	mobile-install mobile-doctor mobile-add-android mobile-add-ios \
	mobile-sync mobile-open-android mobile-open-ios \
	ollama-pull ollama-list \
	tunnel-check \
	up-local logs-local down-local \
	up-insecure down-insecure \
	up-cloudflare logs-cloudflare down-cloudflare \
	up-tunnel logs-tunnel down-tunnel \
	up-lean-tunnel logs-lean-tunnel down-lean-tunnel
help:
	@echo "Targets:"
	@echo "Host policy:"
	@echo "  make context-status # Show invocation context (host/user/pwd/ssh/tty)"
	@echo "  make host-role-status # Show detected HOST_ROLE/hostname and command policy"
	@echo "  make ops-status      # Show host policy plus workflow references"
	@echo "  make ops-patch       # Print the patch workflow for the current host role"
	@echo "  make ops-release     # Print the stable release workflow for the current host role"
	@echo "  make ops-hotfix      # Print the production hotfix workflow for the current host role"
	@echo "  make ops-experiment  # Print the experimental feature workflow"
	@echo "  make ops-rollback    # Print the rollback workflow"
	@echo ""
	@echo "Modes:"
	@echo "  make dev            # Run Odoo natively on host over Docker PostgreSQL (DB=<client> pins one DB; empty keeps manager)"
	@echo "  make dev-safe       # Run Odoo natively on host over local PostgreSQL (DB=<client> pins one DB; empty keeps manager)"
	@echo "  make up-home        # Switch to the normal home stack (same as up, after down-tunnel)"
	@echo "  make up-cowork      # Switch to cowork stack (tunnel + local URL)"
	@echo "  make up-dev         # Switch to localhost-only dev stack"
	@echo "  make up-project     # Switch to host-backend + Docker DB mode"
	@echo "  make down-home      # Stop the normal home stack"
	@echo "  make down-cowork    # Stop the cowork/tunnel stack"
	@echo "  make down-dev       # Stop the localhost-only dev stack"
	@echo "  make down-project   # Stop the host-backend + Docker DB mode"
	@echo "  make logs-home      # Tail logs for the normal home stack"
	@echo "  make logs-cowork    # Tail logs for the cowork/tunnel stack"
	@echo "  make logs-dev       # Tail logs for the localhost-only dev stack"
	@echo "  make logs-project   # Tail logs for the host-backend + Docker DB mode"
	@echo ""
	@echo "Stacks:"
	@echo "  make up             # Start the local/home stack (not the public internet path)"
	@echo "  make up-base        # Start the stable stack with the plain Odoo runtime"
	@echo "  make up-cpu         # Same as up (CPU mode default for Ollama; local/home)"
	@echo "  make up-gpu         # Start local/home stack with optional Ollama GPU override"
	@echo "  make up-local       # Local dev via nginx on $(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT) (websocket-safe)"
	@echo "  make down-base      # Stop the stable plain-runtime stack"
	@echo "  make down-local     # Stop local-dev stack"
	@echo "  make logs-base      # Tail logs for the stable plain-runtime stack"
	@echo "  make logs-local     # Tail local-dev logs (nginx + odoo + db + ollama)"
	@echo "  make up-insecure    # Quick test: expose Odoo 8069/8072 (UNSAFE)"
	@echo "  make down-insecure  # Stop insecure stack"
	@echo "  make up-tunnel      # Default internet publishing path via Cloudflare Tunnel"
	@echo "  make down-tunnel    # Stop Cloudflare Tunnel mode stack"
	@echo "  make logs-tunnel    # Tail cloudflared + nginx + odoo logs"
	@echo "  make tunnel-check SUBDOMAIN=name # Check public reachability for a tenant subdomain"
	@echo "  make up-lean-tunnel # Lean Tunnel: local HTTP (80/8069) + CF Tunnel Internet"
	@echo "  make down-lean-tunnel # Stop Lean Tunnel mode"
	@echo "  make logs-lean-tunnel # Tail Lean Tunnel logs"

	@echo ""
	@echo "Health:"
	@echo "  make smoke-home     # Smoke check for normal local/home mode"
	@echo "  make smoke-cowork   # Smoke check for cowork/tunnel mode"
	@echo "  make smoke-dev      # Smoke check for localhost-only dev mode"
	@echo "  make smoke-project  # Smoke check for host-backend + Docker DB mode"
	@echo "  make troubleshoot-home # Diagnose normal local/home mode"
	@echo "  make troubleshoot-cowork # Diagnose cowork/tunnel mode"
	@echo "  make troubleshoot-dev # Diagnose localhost-only dev mode"
	@echo "  make troubleshoot-project # Diagnose host-backend + Docker DB mode"
	@echo "  make smoke          # Quick health check (local/websocket/public)"
	@echo "  make troubleshoot   # Diagnose env, services, local/public HTTP and websocket"
	@echo "                      # Use SMOKE_PUBLIC=0 to skip public domain check"
	@echo ""
	@echo "Config:"
	@echo "  make env-init       # Create .env from .env.example if missing"
	@echo "  make config-list    # List every .conf/.env-style file in the repo"
	@echo "  make config-view FILE=path # View one config file (or choose interactively)"
	@echo "  make config-view-all # Print all config files with section headers"
	@echo "  make config-edit FILE=path # Edit one config file (or choose interactively)"
	@echo "  make config-create FILE=path [FROM=template] # Create a config file and open it"
	@echo "  make clean          # Remove python cache and logs"
	@echo "  make clean-all      # Deep clean: caches, logs, node_modules, and build artifacts"
	@echo "  make prod-config    # Generate $(PROD_CONFIG) from local secrets"
	@echo "  make refresh-safe   # Regenerate active configs and reload only the Odoo process"
	@echo "  make safe-refresh   # Alias for make refresh-safe"

	@echo "  make dev-host-config # Generate $(DEV_HOST_CONFIG) from local secrets"
	@echo "  make dev-project-config # Generate $(DEV_PROJECT_CONFIG) from local secrets"
	@echo "  make odoo-fix-url   # Force Odoo base URL for DB=$(DB) (or BASE_URL=https://...)"
	@echo ""
	@echo "Database:"
	@echo "  make db-init        # Open Odoo database manager over Docker PostgreSQL to create/use DB ($(DB))"
	@echo "  make db-check       # Check if base module exists in DB"
	@echo "  make db-list        # List reachable PostgreSQL databases and tags"
	@echo "  make db-manager     # Open the interactive database manager"
	@echo "  make prod-db-create # Ensure production database $(PROD_DB_NAME) exists"
	@echo "  make prod-db-init   # Install Odoo base on $(PROD_DB_NAME) when the DB is still empty"
	@echo "  make prod-db-ensure # Create/init production DB on fresh servers before compose up"
	@echo "  make tenant-provision DB=name # Create/init tenant DB and fix URL to https://<db>.$(DOMAIN)"
	@echo "  make tenant-install-modules DB=name TENANT_BOOTSTRAP_MODULES=mod1,mod2 # Install/upgrade tenant module set"
	@echo "  make tenant-check DB=name # Validate DB, frozen base URL, and local Host routing"
	@echo "  make tenant-smoke DB=name [TENANT_SMOKE_PUBLIC=0] # Probe tenant login locally and, optionally, via public URL"
	@echo "  make tenant-bootstrap-defaults DB=name [TENANT_COMPANY_NAME=...] [TENANT_OWNER_LOGIN=...] # Apply company/admin/lang/currency defaults"
	@echo "  make tenant-adjust DB=name # Reapply base URL/freeze and rerun tenant validation"
	@echo "  make tenant-reset DB=name TENANT_PROFILE=... # Drop and recreate a tenant database"
	@echo "  make tenant-user-list DB=name # List interactive users from a tenant database"
	@echo "  make tenant-user-password DB=name LOGIN=user PASSWORD=secret # Reset one tenant user password"
	@echo "  make tenant-user-role DB=name LOGIN=user ROLE=portal|internal|operator # Change one tenant user role"
	@echo "  make tenant-user-create-operator DB=name LOGIN=me@example.com NAME='Operator' PASSWORD=secret # Create/update one tenant operator"
	@echo "  make tenant-user-create-portal DB=name LOGIN=user@example.com NAME='Portal User' PASSWORD=secret # Create one tenant portal user"
	@echo "  make tenant-user-create-client DB=name LOGIN=user@example.com NAME='Client User' PASSWORD=secret # Alias for tenant portal user"
	@echo "  make root-smoke # Validate kodoo.online locally and publicly"
	@echo ""
	@echo "Containers:"
	@echo "  make build          # Build Docker images"
	@echo "  make build-base     # Build the plain Odoo runtime image"
	@echo "  make status         # Show compose status"
	@echo "  make status-base    # Show compose status for the plain-runtime stack"
	@echo "  make logs           # Tail odoo + nginx logs"
	@echo "  make stop           # Stop all modes and free service ports ($(STOP_PORTS))"
	@echo "  make odoo-start CONFIG=... DB=... HTTP_PORT=... # Generic host boot pinned to one DB"
	@echo "  make odoo-manager CONFIG=... DB_SETUP=local|docker|none DB=... HTTP_PORT=... # Generic host boot with database manager"
	@echo "  make odoo-stop PID_FILE=... # Stop a host-run Odoo started with odoo-start/odoo-manager"
	@echo "  make odoo-status PID_FILE=... HTTP_PORT=... # Check a host-run Odoo started with odoo-start/odoo-manager"
	@echo "  make odoo-tui       # Open interactive terminal inside Odoo container"
	@echo "  make odoo-shell     # Open Odoo interactive shell (DB=$(DB))"
	@echo ""
	@echo "Dev Host:"
	@echo "  make dev-host-db-setup # Prepare local PostgreSQL with $(DEV_HOST_DB) and $(DEV_HOST_TEST_DB)"
	@echo "  make dev-host-db-init  # Open Odoo database manager on local PostgreSQL to create/use $(DEV_HOST_DB)"
	@echo "  make dev-host-test-init # Open Odoo database manager on local PostgreSQL to create/use $(DEV_HOST_TEST_DB)"
	@echo "  make dev-host-up    # Run Odoo on host using local PostgreSQL with database manager on $(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)"
	@echo "  make dev-host-upgrade # Upgrade $(DEV_MODULES) on $(DEV_UPGRADE_DB) without opening HTTP"
	@echo "  make dev-host-stop  # Stop local host-run Odoo"
	@echo "  make dev-host-logs  # Tail local host-run Odoo log"
	@echo "  make dev-host-status # Check local host-run Odoo status"
	@echo "  make dev            # Run host Odoo against Docker PostgreSQL on $(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT) (optional DB=<client>)"
	@echo "  make dev-stop       # Stop the shared-DB native Odoo without stopping Docker PostgreSQL"
	@echo "  make dev-logs       # Tail shared-DB native Odoo log"
	@echo "  make dev-status     # Check shared-DB native Odoo and Docker PostgreSQL status"
	@echo "  make dev-safe       # Run host Odoo against local PostgreSQL on $(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT) (optional DB=<client>)"
	@echo "  make dev-safe-stop  # Stop the local-DB native Odoo database-manager mode"
	@echo "  make dev-safe-logs  # Tail local-DB native Odoo database-manager log"
	@echo "  make dev-safe-status # Check local-DB native Odoo database-manager status"
	@echo "  make dev-project-db-setup # Start Docker PostgreSQL and ensure $(DEV_PROJECT_DB) exists (shares Docker DB service)"
	@echo "  make dev-project-db-init # Open Odoo database manager over Docker PostgreSQL to create/use $(DEV_PROJECT_DB)"
	@echo "  make dev-project-up # Run Odoo on host against Docker PostgreSQL with database manager on $(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT)"
	@echo "  make dev-project-stop # Stop host-run Odoo and Docker PostgreSQL"
	@echo "  make dev-project-logs # Tail host-run Odoo log for project mode"
	@echo "  make dev-project-status # Check host-run Odoo and Docker PostgreSQL status"
	@echo "  make dev-host-backup # Dump $(DEV_HOST_DB) to $(BACKUP_DIR)"
	@echo "  make dev-host-restore-ktest # Restore latest backup into $(DEV_HOST_TEST_DB)"
	@echo ""
	@echo "Assets:"
	@echo "  make assets-rebuild # Clear and rebuild Odoo web assets"
	@echo "  make assets-reset   # Hard reset assets (DB + force 'web' module upgrade)"
	@echo ""
	@echo "Utility:"
	@echo "  make doctor         # Check OS/WSL/GPU/Docker status"
	@echo "  make deps-install   # Install only required host deps (OS-aware, GPU-aware)"
	@echo "  make up-smoke       # Start tunnel/public stack and run smoke checks"
	@echo "  make odoo-lnav      # Run local Odoo and tail logs with lnav or tail"
	@echo "  make tui            # Build and open the Go Bubble Tea control plane"
	@echo "  make tui-live       # Alias for make tui"
	@echo "  make tui-install    # Download Go deps and build $(KODOO_TUI_BIN)"
	@echo "  make tui-menu       # Open the shell-based legacy Make menu"
	@echo "  make tui-doctor     # Check Go TUI runtime prerequisites"
	@echo ""
	@echo "Mobile:"
	@echo "  make mobile-install # Install mobile app dependencies in $(MOBILE_DIR)"
	@echo "  make mobile-doctor  # Run Capacitor doctor for the mobile app"
	@echo "  make mobile-add-android # Generate Android shell"
	@echo "  make mobile-add-ios # Generate iOS shell"
	@echo "  make mobile-sync    # Sync Capacitor config and web assets"
	@echo "  make mobile-open-android # Open Android Studio project"
	@echo "  make mobile-open-ios # Open Xcode project"
	@echo ""
	@echo "Ollama:"
	@echo "  make ollama-pull    # Pull default model in Ollama ($(OLLAMA_MODEL))"
	@echo "  make ollama-list    # List local Ollama models"
	@echo ""
	@echo "Examples:"
	@echo "  cp .env.example .env"

context-status:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh

host-role-status:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh
	@case "$(HOST_ROLE)" in \
	  dex00) \
	    echo "Policy: development and validation host."; \
	    echo "Allowed: make dev, make dev-safe, make dev-host-up, tests, local experiments."; \
	    echo "Blocked: production/stable publish targets such as make up-tunnel and make refresh-safe."; \
	    ;; \
	  dex01) \
	    echo "Policy: bastion/operations host."; \
	    echo "Allowed: production deploy orchestration, patch/release/rollback commands, SSH to srv-01."; \
	    echo "Avoid: day-to-day development targets."; \
	    ;; \
	  srv01) \
	    echo "Policy: stable production runtime."; \
	    echo "Allowed: stable Docker runtime, refresh, smoke, logs, backup/restore, rollback."; \
	    echo "Blocked: host-run dev targets such as make dev and make dev-safe."; \
	    ;; \
	  *) \
	    echo "Policy: unknown host."; \
	    echo "Safety mode: explicit dex-00 and srv-01 restrictions apply, but unknown hosts are not hard-blocked."; \
	    echo "Set HOST_ROLE=dex00|dex01|srv01 if you want deterministic policy outside the named hosts."; \
	    ;; \
	esac; \
	echo "Workflow reference: $(OPERATIONS_DOC)"

guard-dev-host:
	@case "$(HOST_ROLE)" in \
	  srv01) \
	    echo "ERROR: development host targets are blocked on srv-01."; \
	    echo "Run dev flows on dex-00. See $(OPERATIONS_DOC)."; \
	    HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh; \
	    exit 1; \
	    ;; \
	  dex01) \
	    echo "ERROR: development host targets are blocked on dex-01."; \
	    echo "Use dex-00 for dev workflows. See $(OPERATIONS_DOC)."; \
	    HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh; \
	    exit 1; \
	    ;; \
	  *) ;; \
	esac

guard-prod-host:
	@case "$(HOST_ROLE)" in \
	  dex00) \
	    echo "ERROR: production/stable targets are blocked on dex-00."; \
	    echo "Use dex-01 for bastion operations or srv-01 for the stable runtime. See $(OPERATIONS_DOC)."; \
	    HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh; \
	    exit 1; \
	    ;; \
	  *) ;; \
	esac

ops-status: host-role-status
	@echo "Suggested commands:"
	@case "$(HOST_ROLE)" in \
	  dex00) echo "  make dev-safe"; echo "  make dev"; echo "  make ops-experiment";; \
	  dex01) echo "  make ops-patch"; echo "  make ops-release"; echo "  make ops-rollback";; \
	  srv01) echo "  make status"; echo "  make smoke"; echo "  make logs"; echo "  make ops-rollback";; \
	  *) echo "  make host-role-status"; echo "  make ops-patch";; \
	esac

ops-patch:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh
	@echo "Patch workflow ($(HOST_ROLE))"; \
	echo "1. Implement and validate on dex-00 with make dev-safe or make dev."; \
	echo "2. Run targeted tests and smoke checks on the candidate database."; \
	echo "3. From dex-01, review the exact revision to deploy and prepare rollback point."; \
	echo "4. On srv-01, take/verify backup, deploy the validated revision, then run make refresh-safe."; \
	echo "5. Run make smoke and inspect make logs on srv-01 before closing the patch."; \
	echo "Reference: $(OPERATIONS_DOC)"

ops-release:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh
	@echo "Stable release workflow ($(HOST_ROLE))"; \
	echo "1. Build and validate the release candidate only on dex-00."; \
	echo "2. Freeze the revision, migration notes, and operator checklist."; \
	echo "3. Use dex-01 as the bastion to connect to srv-01 and execute the deploy sequence."; \
	echo "4. On srv-01 run backup, update the stable stack, then make refresh-safe or the approved stack restart."; \
	echo "5. Confirm smoke, logs, websocket health, and public endpoint before declaring release complete."; \
	echo "Reference: $(OPERATIONS_DOC)"

ops-hotfix:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh
	@echo "Production hotfix workflow ($(HOST_ROLE))"; \
	echo "1. Reproduce and fix on dex-00 using the smallest viable change."; \
	echo "2. Validate against the closest safe copy of production data."; \
	echo "3. From dex-01, prepare backup plus rollback command before touching srv-01."; \
	echo "4. Apply on srv-01, run make refresh-safe, then make smoke immediately."; \
	echo "5. If verification fails, execute rollback first and continue diagnosis off-production."; \
	echo "Reference: $(OPERATIONS_DOC)"

ops-experiment:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh
	@echo "Experimental feature workflow ($(HOST_ROLE))"; \
	echo "1. Experiments live only on dex-00."; \
	echo "2. Use isolated local PostgreSQL with make dev-safe whenever possible."; \
	echo "3. Keep experiment branches and databases separate from stable release candidates."; \
	echo "4. Promote to a patch/release workflow only after validation is complete."; \
	echo "Reference: $(OPERATIONS_DOC)"

ops-rollback:
	@HOST_ROLE="$(HOST_ROLE)" MAKE_CONTEXT_COMMAND="make $(ORIGINAL_MAKE_GOALS)" bash ./scripts/invocation-context.sh
	@echo "Rollback workflow ($(HOST_ROLE))"; \
	echo "1. Keep the last known-good revision and latest backup identified before every deploy."; \
	echo "2. On failure, stop the rollout, restore the known-good app revision, and restore data only if required."; \
	echo "3. Re-run make smoke, inspect make logs, and confirm public availability on srv-01."; \
	echo "4. Investigate the failed candidate later on dex-00, never on the live srv-01 runtime."; \
	echo "Reference: $(OPERATIONS_DOC)"

doctor:
	@echo "== Host =="
	@echo "OS: $$(uname -s)"
	@echo "Kernel: $$(uname -r)"
	@if grep -qi microsoft /proc/version 2>/dev/null; then echo "WSL: yes"; else echo "WSL: no"; fi
	@echo ""
	@echo "== Tools =="
	@if command -v docker >/dev/null 2>&1; then docker --version; else echo "docker: missing"; fi
	@if command -v docker >/dev/null 2>&1; then $(COMPOSE) version; else true; fi
	@if command -v nvidia-smi >/dev/null 2>&1; then echo "GPU: NVIDIA detected"; nvidia-smi -L; else echo "GPU: not detected (CPU mode recommended)"; fi

deps-install:
	@set -e; \
	OS="$$(uname -s)"; \
	echo "Installing minimal dependencies for $$OS ..."; \
	if [ "$$OS" = "Linux" ]; then \
	  if command -v apt-get >/dev/null 2>&1; then \
	    sudo apt-get update; \
	    sudo apt-get install -y ca-certificates curl make jq; \
	    if command -v nvidia-smi >/dev/null 2>&1; then \
	      echo "NVIDIA GPU detected: installing nvidia-container-toolkit"; \
	      sudo apt-get install -y nvidia-container-toolkit || true; \
	    else \
	      echo "No NVIDIA GPU detected: skipping nvidia-container-toolkit."; \
	    fi; \
	  elif command -v pacman >/dev/null 2>&1; then \
	    sudo pacman -Syu --noconfirm ca-certificates curl make jq; \
	    if command -v nvidia-smi >/dev/null 2>&1; then \
	      echo "NVIDIA GPU detected: install nvidia-container-toolkit manually if needed."; \
	    fi; \
	  elif command -v dnf >/dev/null 2>&1; then \
	    sudo dnf install -y ca-certificates curl make jq; \
	  else \
	    echo "Unsupported Linux package manager. Install: ca-certificates curl make jq"; \
	  fi; \
	else \
		echo "Non-Linux host: install Docker Desktop + make + curl manually."; \
	fi

env-init:
	@if [ -f .env ]; then \
	  echo ".env already exists."; \
	elif [ -f .env.example ]; then \
	  cp .env.example .env; \
	  echo "Created .env from .env.example."; \
	elif [ -f .env.make ]; then \
	  cp .env.make .env; \
	  echo "Created .env from existing .env.make."; \
	else \
	  echo "Missing .env.example. Create it first."; \
	  exit 1; \
	fi

config-list:
	@set -e; \
	mapfile -t files < <($(CONFIG_FIND_CMD)); \
	if [ "$${#files[@]}" -eq 0 ]; then \
	  echo "No .conf/.env-style files found."; \
	  exit 0; \
	fi; \
	printf "Config files found (%s):\n" "$${#files[@]}"; \
	for file in "$${files[@]}"; do \
	  printf "  %s\n" "$$file"; \
	done

config-view:
	@set -e; \
	file="$(FILE)"; \
	if [ -z "$$file" ]; then \
	  mapfile -t files < <($(CONFIG_FIND_CMD)); \
	  if [ "$${#files[@]}" -eq 0 ]; then \
	    echo "No .conf/.env-style files found."; \
	    exit 1; \
	  fi; \
	  printf "Select a config file to view:\n"; \
	  for i in "$${!files[@]}"; do \
	    printf "  [%s] %s\n" "$$((i + 1))" "$${files[$$i]}"; \
	  done; \
	  printf "Number: "; \
	  read -r choice; \
	  case "$$choice" in \
	    ''|*[!0-9]*) echo "ERROR: enter a numeric selection."; exit 1 ;; \
	  esac; \
	  if [ "$$choice" -lt 1 ] || [ "$$choice" -gt "$${#files[@]}" ]; then \
	    echo "ERROR: selection out of range."; \
	    exit 1; \
	  fi; \
	  file="$${files[$$((choice - 1))]}"; \
	fi; \
	if [ ! -f "$$file" ]; then \
	  echo "ERROR: file '$$file' not found."; \
	  exit 1; \
	fi; \
	if command -v less >/dev/null 2>&1 && [ -t 1 ]; then \
	  less "$$file"; \
	else \
	  cat "$$file"; \
	fi

config-view-all:
	@set -e; \
	mapfile -t files < <($(CONFIG_FIND_CMD)); \
	if [ "$${#files[@]}" -eq 0 ]; then \
	  echo "No .conf/.env-style files found."; \
	  exit 0; \
	fi; \
	if command -v less >/dev/null 2>&1 && [ -t 1 ]; then \
	  { \
	    for file in "$${files[@]}"; do \
	      printf "\n===== %s =====\n" "$$file"; \
	      cat "$$file"; \
	    done; \
	  } | less; \
	else \
	  for file in "$${files[@]}"; do \
	    printf "\n===== %s =====\n" "$$file"; \
	    cat "$$file"; \
	  done; \
	fi

config-edit:
	@set -e; \
	file="$(FILE)"; \
	if [ -z "$$file" ]; then \
	  mapfile -t files < <($(CONFIG_FIND_CMD)); \
	  if [ "$${#files[@]}" -eq 0 ]; then \
	    echo "No .conf/.env-style files found."; \
	    exit 1; \
	  fi; \
	  printf "Select a config file to edit:\n"; \
	  for i in "$${!files[@]}"; do \
	    printf "  [%s] %s\n" "$$((i + 1))" "$${files[$$i]}"; \
	  done; \
	  printf "Number: "; \
	  read -r choice; \
	  case "$$choice" in \
	    ''|*[!0-9]*) echo "ERROR: enter a numeric selection."; exit 1 ;; \
	  esac; \
	  if [ "$$choice" -lt 1 ] || [ "$$choice" -gt "$${#files[@]}" ]; then \
	    echo "ERROR: selection out of range."; \
	    exit 1; \
	  fi; \
	  file="$${files[$$((choice - 1))]}"; \
	fi; \
	if [ ! -f "$$file" ]; then \
	  echo "ERROR: file '$$file' not found."; \
	  exit 1; \
	fi; \
	editor="$(CONFIG_EDITOR)"; \
	if [ -z "$$editor" ]; then \
	  if [ -n "$$VISUAL" ]; then \
	    editor="$$VISUAL"; \
	  elif [ -n "$$EDITOR" ]; then \
	    editor="$$EDITOR"; \
	  elif command -v nano >/dev/null 2>&1; then \
	    editor="nano"; \
	  elif command -v vi >/dev/null 2>&1; then \
	    editor="vi"; \
	  else \
	    echo "ERROR: no editor found. Set EDITOR, VISUAL, or CONFIG_EDITOR."; \
	    exit 1; \
	  fi; \
	fi; \
	eval "$$editor \"$$file\""

config-create:
	@set -e; \
	file="$(FILE)"; \
	template="$(FROM)"; \
	if [ -z "$$file" ]; then \
	  printf "Enter the new config file path (.conf, .env, .env.*): "; \
	  read -r file; \
	fi; \
	case "$$file" in \
	  *.conf|*.env|*.env.*|.env|.env.*) ;; \
	  *) \
	    echo "ERROR: FILE must end with .conf, .env, or .env.*"; \
	    exit 1 ;; \
	esac; \
	if [ -e "$$file" ]; then \
	  echo "Config file '$$file' already exists."; \
	  $(MAKE) config-edit FILE="$$file"; \
	  exit 0; \
	fi; \
	mkdir -p "$$(dirname "$$file")"; \
	if [ -z "$$template" ] && [ -f "$$file.example" ]; then \
	  template="$$file.example"; \
	fi; \
	if [ -z "$$template" ] && [[ "$$file" == *.local.conf ]]; then \
	  inferred_template="$${file%.local.conf}.conf.example"; \
	  if [ -f "$$inferred_template" ]; then \
	    template="$$inferred_template"; \
	  fi; \
	fi; \
	if [ -n "$$template" ]; then \
	  if [ ! -f "$$template" ]; then \
	    echo "ERROR: template '$$template' not found."; \
	    exit 1; \
	  fi; \
	  cp "$$template" "$$file"; \
	  echo "Created '$$file' from '$$template'."; \
	else \
	  : > "$$file"; \
	  echo "Created empty config file '$$file'."; \
	fi; \
	$(MAKE) config-edit FILE="$$file"

prod-config:
	@CONFIG_OUTPUT="$(PROD_CONFIG)" \
	PROD_ADMIN_PASSWORD="$(PROD_ADMIN_PASSWORD)" \
	PROD_DB_HOST="db" \
	PROD_DB_PORT="5432" \
	PROD_DB_USER="$(PROD_DB_USER)" \
	PROD_DB_PASSWORD="$(PROD_DB_PASSWORD)" \
	./scripts/render-prod-config.sh
	@chmod 644 "$(PROD_CONFIG)"
	@echo "Generated $(PROD_CONFIG) from $(ENV_FILE) (chmod 644)."

dev-host-config:
	@CONFIG_OUTPUT="$(DEV_HOST_CONFIG)" \
	DEV_HOST_ADMIN_PASSWORD="$(DEV_HOST_ADMIN_PASSWORD)" \
	APP_DB_HOST="$(PG_LOCAL_HOST)" \
	APP_DB_PORT="$(PG_LOCAL_PORT)" \
	APP_DB_USER="$(PG_LOCAL_USER)" \
	APP_DB_PASSWORD="$(PG_LOCAL_PASSWORD)" \
	APP_HTTP_PORT="$(DEV_HOST_HTTP_PORT)" \
	./scripts/render-dev-host-config.sh
	@chmod 644 "$(DEV_HOST_CONFIG)"
	@echo "Generated $(DEV_HOST_CONFIG) from $(ENV_FILE) (chmod 644)."

dev-project-config:
	@CONFIG_OUTPUT="$(DEV_PROJECT_CONFIG)" \
	DEV_HOST_ADMIN_PASSWORD="$(if $(DEV_PROJECT_ADMIN_PASSWORD),$(DEV_PROJECT_ADMIN_PASSWORD),$(if $(DEV_HOST_ADMIN_PASSWORD),$(DEV_HOST_ADMIN_PASSWORD),$(PROD_ADMIN_PASSWORD)))" \
	APP_DB_HOST="$(DOCKER_DB_BIND_HOST)" \
	APP_DB_PORT="$(DOCKER_DB_HOST_PORT)" \
	APP_DB_USER="$(PROD_DB_USER)" \
	APP_DB_PASSWORD="$(PROD_DB_PASSWORD)" \
	APP_HTTP_PORT="$(DEV_PROJECT_HTTP_PORT)" \
	./scripts/render-dev-host-config.sh
	@chmod 644 "$(DEV_PROJECT_CONFIG)"
	@echo "Generated $(DEV_PROJECT_CONFIG) from $(ENV_FILE) (chmod 644)."
# Equivalent to scripts/start-with-lnav.ps1 for Linux/WSL environments.
odoo-lnav:
	@$(MAKE) ports-clean PORTS="$(DEV_HOST_HTTP_PORT)"
	@mkdir -p "$$(dirname "$(LOG_PATH)")"
	@echo "Starting Odoo ($(DB)) -> $(LOG_PATH)"
	@nohup $(PYTHON) $(ODOO_BIN) -c $(CONFIG) -d $(DB) --logfile="$(LOG_PATH)" --log-level=info >/dev/null 2>&1 &
	@echo "Odoo started in background. PID: $$!"
	@if command -v lnav >/dev/null 2>&1; then \
		echo "Launching lnav on $(LOG_PATH)"; \
		lnav "$(LOG_PATH)"; \
	else \
		echo "lnav not found. Falling back to tail -f"; \
		tail -f "$(LOG_PATH)"; \
	fi

odoo-start:
	@case "$(DB_SETUP)" in \
	  none) ;; \
	  local) \
	    PG_SERVICE="$(PG_LOCAL_SERVICE)" \
	    PG_SUPERUSER="$(PG_LOCAL_SUPERUSER)" \
	    APP_DB_USER="$(PG_LOCAL_USER)" \
	    APP_DB_PASSWORD="$(PG_LOCAL_PASSWORD)" \
	    APP_DB_NAME="$(DB)" \
	    TEST_DB_NAME="$(PREBOOT_TEST_DB)" \
	    CREATE_APP_DATABASES="$(PRECREATE_DB)" \
	    ./scripts/dev-host-db-setup.sh ;; \
	  docker) \
	    echo "WARNING: odoo-start with DB_SETUP=docker shares the Docker DB service."; \
	    COMPOSE_BIN='$(COMPOSE_PROJECT_DB)' \
	    DB_USER="$(PROD_DB_USER)" \
	    DB_PASSWORD="$(PROD_DB_PASSWORD)" \
	    DB_NAME="$(DB)" \
	    CREATE_APP_DATABASE="$(PRECREATE_DB)" \
	    ./scripts/dev-project-db-setup.sh ;; \
	  *) echo "ERROR: DB_SETUP must be one of none, local, docker."; exit 1 ;; \
	esac
	@$(MAKE) ports-clean PORTS="$(HTTP_PORT)"
	@PYTHON_BIN="$(PYTHON)" \
	ODOO_DEV_CONFIG="$(CONFIG)" \
	ODOO_DEV_DB="$(DB)" \
	ODOO_DEV_LOG_PATH="$(LOG_PATH)" \
	ODOO_DEV_PID_FILE="$(PID_FILE)" \
	ODOO_DEV_HTTP_PORT="$(HTTP_PORT)" \
	./scripts/dev-host-start.sh

odoo-manager:
	@case "$(DB_SETUP)" in \
	  none) ;; \
	  local) \
	    PG_SERVICE="$(PG_LOCAL_SERVICE)" \
	    PG_SUPERUSER="$(PG_LOCAL_SUPERUSER)" \
	    APP_DB_USER="$(PG_LOCAL_USER)" \
	    APP_DB_PASSWORD="$(PG_LOCAL_PASSWORD)" \
	    APP_DB_NAME="$(DB)" \
	    TEST_DB_NAME="$(PREBOOT_TEST_DB)" \
	    CREATE_APP_DATABASES="$(PRECREATE_DB)" \
	    ./scripts/dev-host-db-setup.sh ;; \
	  docker) \
	    echo "WARNING: odoo-manager with DB_SETUP=docker shares the Docker DB service."; \
	    COMPOSE_BIN='$(COMPOSE_PROJECT_DB)' \
	    DB_USER="$(PROD_DB_USER)" \
	    DB_PASSWORD="$(PROD_DB_PASSWORD)" \
	    DB_NAME="$(DB)" \
	    CREATE_APP_DATABASE="$(PRECREATE_DB)" \
	    ./scripts/dev-project-db-setup.sh ;; \
	  *) echo "ERROR: DB_SETUP must be one of none, local, docker."; exit 1 ;; \
	esac
	@$(MAKE) ports-clean PORTS="$(HTTP_PORT)"
	@PYTHON_BIN="$(PYTHON)" \
	ODOO_DEV_CONFIG="$(CONFIG)" \
	ODOO_DEV_DB="" \
	ODOO_DEV_LOG_PATH="$(LOG_PATH)" \
	ODOO_DEV_PID_FILE="$(PID_FILE)" \
	ODOO_DEV_HTTP_PORT="$(HTTP_PORT)" \
	./scripts/dev-host-start.sh
	@if [ -n "$(DB)" ]; then \
	  echo "Database manager ready for '$$(printf "%s" "$(DB)")': http://$(LOCAL_BIND_HOST):$(HTTP_PORT)/web/database/manager"; \
	fi

odoo-stop:
	@ODOO_DEV_PID_FILE="$(PID_FILE)" ./scripts/dev-host-stop.sh

odoo-status:
	@set -e; \
	if [ -f "$(PID_FILE)" ] && kill -0 "$$(cat "$(PID_FILE)")" 2>/dev/null; then \
	  echo "Generic host Odoo is running with PID $$(cat "$(PID_FILE)")"; \
	  echo "URL: http://$(LOCAL_BIND_HOST):$(HTTP_PORT)"; \
	  echo "Config: $(CONFIG)"; \
	  echo "Log: $(LOG_PATH)"; \
	else \
	  echo "Generic host Odoo is not running."; \
	fi

build:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(COMPOSE) build

build-base:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(COMPOSE_BASE) build odoo

refresh-safe:
	@$(MAKE) guard-prod-host
	@./scripts/refresh-safe.sh

safe-refresh:
	@$(MAKE) refresh-safe

stop:
	@echo "Stopping all compose modes..."
	@$(MAKE) dev-host-stop >/dev/null 2>&1 || true
	@$(MAKE) dev-project-stop >/dev/null 2>&1 || true
	@$(COMPOSE) down --remove-orphans >/dev/null 2>&1 || true
	@$(COMPOSE_LOCAL) down --remove-orphans >/dev/null 2>&1 || true
	@$(COMPOSE_INSECURE) down --remove-orphans >/dev/null 2>&1 || true
	@$(COMPOSE_TUNNEL) down --remove-orphans >/dev/null 2>&1 || true
	@$(COMPOSE_GPU) down --remove-orphans >/dev/null 2>&1 || true
	@$(COMPOSE_PROJECT_DB) down --remove-orphans >/dev/null 2>&1 || true
	@$(MAKE) ports-clean PORTS="$(STOP_PORTS)"
	@echo "Stop complete."

ports-clean:
	@set -e; \
	PORTS="$(PORTS)"; \
	if [ -z "$$PORTS" ]; then echo "No ports requested for cleanup."; exit 0; fi; \
	for p in $$PORTS; do \
	  echo "Checking port $$p..."; \
	  pids=$$( (ss -ltnp "sport = :$$p" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || \
	            lsof -ti:$$p 2>/dev/null || \
	            fuser $$p/tcp 2>/dev/null | awk '{print $$1}') | sort -u | tr '\n' ' ' ); \
	  if [ -n "$$pids" ]; then \
	    echo "  Releasing port $$p (PIDs: $$pids)"; \
	    kill -TERM $$pids 2>/dev/null || true; \
	    sleep 1; \
	    remaining=$$( (ss -ltnp "sport = :$$p" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || \
	                   lsof -ti:$$p 2>/dev/null) | sort -u | tr '\n' ' ' ); \
	    if [ -n "$$remaining" ]; then \
	      kill -KILL $$remaining 2>/dev/null || true; \
	    fi; \
	  else \
	    echo "  Port $$p already free."; \
	  fi; \
	done

up: up-cpu

up-base:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(PUBLIC_HTTP_PORT) $(PUBLIC_HTTPS_PORT)"
	@$(MAKE) prod-db-ensure
	@$(COMPOSE_BASE) up -d db odoo nginx ollama
	@$(MAKE) ollama-pull
	@echo "Stable plain Odoo runtime: https://$(DOMAIN)"

up-home:
	@$(MAKE) down-tunnel >/dev/null 2>&1 || true
	@$(MAKE) dev-host-stop >/dev/null 2>&1 || true
	@$(MAKE) dev-project-stop >/dev/null 2>&1 || true
	@$(MAKE) up

down-home:
	@$(MAKE) down

logs-home:
	@$(MAKE) logs

smoke-home:
	@$(MAKE) smoke SMOKE_PUBLIC=0

troubleshoot-home:
	@$(MAKE) troubleshoot SMOKE_PUBLIC=0

up-cowork:
	@$(MAKE) down >/dev/null 2>&1 || true
	@$(MAKE) dev-host-stop >/dev/null 2>&1 || true
	@$(MAKE) dev-project-stop >/dev/null 2>&1 || true
	@$(MAKE) up-tunnel

down-cowork:
	@$(MAKE) down-tunnel

logs-cowork:
	@$(MAKE) logs-tunnel

smoke-cowork:
	@$(MAKE) smoke

troubleshoot-cowork:
	@$(MAKE) troubleshoot

up-dev:
	@$(MAKE) down >/dev/null 2>&1 || true
	@$(MAKE) dev-host-stop >/dev/null 2>&1 || true
	@$(MAKE) dev-project-stop >/dev/null 2>&1 || true
	@$(MAKE) up-local

dev:
	@$(MAKE) guard-dev-host
	@selected_db="$(strip $(DB))"; \
	db_name="$${selected_db:-$(DEV_PROJECT_DB)}"; \
	precreate=0; \
	if [ -n "$$selected_db" ]; then precreate=1; fi; \
	$(MAKE) dev-host-stop >/dev/null 2>&1 || true; \
	ODOO_DEV_PID_FILE="$(DEV_PROJECT_PID_FILE)" ./scripts/dev-host-stop.sh >/dev/null 2>&1 || true; \
	$(MAKE) ports-clean PORTS="$(DEV_PROJECT_HTTP_PORT)"; \
	$(MAKE) dev-project-db-setup DEV_PROJECT_DB="$$db_name" DEV_PROJECT_PRECREATE_DATABASE="$$precreate"; \
	$(MAKE) dev-project-config; \
	PYTHON_BIN="$(PYTHON)" \
	ODOO_DEV_CONFIG="$(DEV_PROJECT_CONFIG)" \
	ODOO_DEV_DB="$$selected_db" \
	ODOO_DEV_LOG_PATH="$(DEV_PROJECT_LOG_PATH)" \
	ODOO_DEV_PID_FILE="$(DEV_PROJECT_PID_FILE)" \
	ODOO_DEV_HTTP_PORT="$(DEV_PROJECT_HTTP_PORT)" \
	./scripts/dev-host-start.sh
	@$(MAKE) dev-logs

dev-stop:
	@ODOO_DEV_PID_FILE="$(DEV_PROJECT_PID_FILE)" ./scripts/dev-host-stop.sh

dev-logs:
	@mkdir -p "$(dir $(DEV_PROJECT_LOG_PATH))"
	@touch "$(DEV_PROJECT_LOG_PATH)"
	@if command -v lnav >/dev/null 2>&1; then \
		echo "Launching lnav on $(DEV_PROJECT_LOG_PATH)"; \
		lnav "$(DEV_PROJECT_LOG_PATH)"; \
	elif command -v ccze >/dev/null 2>&1; then \
		echo "lnav not found. Falling back to tail -f | ccze"; \
		tail -f "$(DEV_PROJECT_LOG_PATH)" | ccze -A; \
	else \
		echo "Neither lnav nor ccze found. Falling back to tail -f"; \
		tail -f "$(DEV_PROJECT_LOG_PATH)"; \
	fi

dev-status:
	@set -e; \
	if [ -f "$(DEV_PROJECT_PID_FILE)" ] && kill -0 "$$(cat "$(DEV_PROJECT_PID_FILE)")" 2>/dev/null; then \
	  echo "Shared-DB native Odoo is running with PID $$(cat "$(DEV_PROJECT_PID_FILE)")"; \
	  echo "URL: http://$(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT)"; \
	  echo "Database manager: http://$(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT)/web/database/manager"; \
	else \
	  echo "Shared-DB native Odoo is not running."; \
	fi; \
	docker inspect -f '{{.State.Status}}' kodoo-db 2>/dev/null | sed 's/^/Docker PostgreSQL: /' || echo "Docker PostgreSQL: not running"; \
	echo "Database endpoint: $(DOCKER_DB_BIND_HOST):$(DOCKER_DB_HOST_PORT)"

dev-safe:
	@$(MAKE) guard-dev-host
	@selected_db="$(strip $(DB))"; \
	db_name="$${selected_db:-$(DEV_HOST_DB)}"; \
	precreate=0; \
	if [ -n "$$selected_db" ]; then precreate=1; fi; \
	$(MAKE) dev-host-stop >/dev/null 2>&1 || true; \
	$(MAKE) ports-clean PORTS="$(DEV_HOST_HTTP_PORT)"; \
	$(MAKE) dev-host-db-setup DEV_HOST_DB="$$db_name" DEV_HOST_PRECREATE_DATABASES="$$precreate"; \
	$(MAKE) dev-host-config; \
	PYTHON_BIN="$(PYTHON)" \
	ODOO_DEV_CONFIG="$(DEV_HOST_CONFIG)" \
	ODOO_DEV_DB="$$selected_db" \
	ODOO_DEV_LOG_PATH="$(DEV_HOST_LOG_PATH)" \
	ODOO_DEV_PID_FILE="$(DEV_HOST_PID_FILE)" \
	ODOO_DEV_HTTP_PORT="$(DEV_HOST_HTTP_PORT)" \
	./scripts/dev-host-start.sh

dev-safe-stop:
	@$(MAKE) dev-host-stop

dev-safe-logs:
	@$(MAKE) dev-host-logs

dev-safe-status:
	@set -e; \
	if [ -f "$(DEV_HOST_PID_FILE)" ] && kill -0 "$$(cat "$(DEV_HOST_PID_FILE)")" 2>/dev/null; then \
	  echo "Local-DB native Odoo is running with PID $$(cat "$(DEV_HOST_PID_FILE)")"; \
	  echo "URL: http://$(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)"; \
	  echo "Database manager: http://$(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)/web/database/manager"; \
	else \
	  echo "Local-DB native Odoo is not running."; \
	fi; \
	if command -v systemctl >/dev/null 2>&1; then \
	  systemctl is-active "$(PG_LOCAL_SERVICE)" >/dev/null 2>&1 && echo "PostgreSQL service $(PG_LOCAL_SERVICE): active" || echo "PostgreSQL service $(PG_LOCAL_SERVICE): inactive"; \
	fi; \
	echo "Database endpoint: $(PG_LOCAL_HOST):$(PG_LOCAL_PORT)"

down-dev:
	@$(MAKE) down-local

logs-dev:
	@$(MAKE) logs-local

smoke-dev:
	@$(MAKE) smoke SMOKE_PUBLIC=0

troubleshoot-dev:
	@$(MAKE) troubleshoot SMOKE_PUBLIC=0

up-project:
	@$(MAKE) down >/dev/null 2>&1 || true
	@$(MAKE) down-local >/dev/null 2>&1 || true
	@$(MAKE) down-tunnel >/dev/null 2>&1 || true
	@$(MAKE) dev-host-stop >/dev/null 2>&1 || true
	@$(MAKE) dev-project-up

down-project:
	@$(MAKE) dev-project-stop

logs-project:
	@$(MAKE) dev-project-logs

smoke-project:
	@set -e; \
	echo "== Smoke check (project mode / $(DEV_PROJECT_DB)) =="; \
	db_running="$$(docker inspect -f '{{.State.Running}}' kodoo-db 2>/dev/null || true)"; \
	if [ "$$db_running" != "true" ]; then \
	  echo "FAIL: Docker PostgreSQL container 'kodoo-db' is not running."; \
	  exit 1; \
	fi; \
	if [ ! -f "$(DEV_PROJECT_PID_FILE)" ] || ! kill -0 "$$(cat "$(DEV_PROJECT_PID_FILE)" 2>/dev/null)" 2>/dev/null; then \
	  echo "FAIL: host Odoo process for project mode is not running."; \
	  exit 1; \
	fi; \
	code="$$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$(DEV_PROJECT_HTTP_PORT)/odoo" || true)"; \
	if [ "$$code" != "200" ] && [ "$$code" != "303" ]; then \
	  echo "FAIL: local endpoint returned HTTP $$code."; \
	  exit 1; \
	fi; \
	echo "OK: Docker PostgreSQL is running."; \
	echo "OK: host Odoo is running."; \
	echo "OK: local endpoint http://127.0.0.1:$(DEV_PROJECT_HTTP_PORT)/odoo HTTP $$code."

troubleshoot-project:
	@set +e; \
	rc=0; \
	echo "== Troubleshoot (project mode / $(DEV_PROJECT_DB)) =="; \
	echo ""; \
	echo "== Files =="; \
	if [ -f .env ] || [ -f .env.make ]; then echo "OK: env file found."; else echo "FAIL: .env/.env.make missing."; rc=1; fi; \
	if [ -f "$(DEV_PROJECT_CONFIG)" ]; then echo "OK: $(DEV_PROJECT_CONFIG) found."; else echo "WARN: $(DEV_PROJECT_CONFIG) missing. Run: make dev-project-config"; rc=1; fi; \
	echo ""; \
	echo "== Docker DB =="; \
	$(COMPOSE_PROJECT_DB) ps db || rc=1; \
	echo ""; \
	echo "== Host Odoo =="; \
	if [ -f "$(DEV_PROJECT_PID_FILE)" ] && kill -0 "$$(cat "$(DEV_PROJECT_PID_FILE)")" 2>/dev/null; then \
	  echo "OK: host Odoo running with PID $$(cat "$(DEV_PROJECT_PID_FILE)")"; \
	else \
	  echo "FAIL: host Odoo is not running."; \
	  rc=1; \
	fi; \
	echo "Docker PostgreSQL host binding: $(DOCKER_DB_BIND_HOST):$(DOCKER_DB_HOST_PORT)"; \
	echo ""; \
	echo "== Local HTTP =="; \
	code="$$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$(LOCAL_HTTP_PORT)/odoo" || true)"; \
	echo "http://127.0.0.1:$(LOCAL_HTTP_PORT)/odoo -> $$code"; \
	if [ "$$code" != "200" ] && [ "$$code" != "303" ]; then rc=1; fi; \
	echo ""; \
	echo "== Hints =="; \
	echo "make dev-project-up"; \
	echo "make dev-project-db-init"; \
	echo "make dev-project-logs"; \
	exit $$rc

up-cpu:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(PUBLIC_HTTP_PORT) $(PUBLIC_HTTPS_PORT)"
	@$(MAKE) prod-db-ensure
	@$(COMPOSE) up -d db odoo nginx ollama
	@$(MAKE) ollama-pull

up-gpu:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(PUBLIC_HTTP_PORT) $(PUBLIC_HTTPS_PORT)"
	@$(MAKE) prod-db-ensure
	@if ! command -v nvidia-smi >/dev/null 2>&1; then echo "NVIDIA GPU not detected. Use 'make up-cpu'."; exit 1; fi
	@$(COMPOSE_GPU) up -d db odoo nginx ollama
	@$(MAKE) ollama-pull

up-local:
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(LOCAL_HTTP_PORT)"
	@$(MAKE) prod-db-ensure
	@echo "Starting local-dev mode via nginx on $(LOCAL_BIND_HOST) (websocket enabled)."
	@$(COMPOSE_LOCAL) up -d db odoo nginx ollama
	@$(MAKE) ollama-pull
	@echo "Local Odoo: http://$(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT)"

logs-local:
	@$(COMPOSE_LOCAL) logs -f --tail=120 nginx odoo db ollama

logs-base:
	@$(COMPOSE_BASE) logs -f --tail=120 nginx odoo db ollama

down-local:
	@$(COMPOSE_LOCAL) down --remove-orphans

down-base:
	@$(COMPOSE_BASE) down --remove-orphans

down:
	@$(COMPOSE) down --remove-orphans

status:
	@$(COMPOSE) ps

status-base:
	@$(COMPOSE_BASE) ps

logs:
	@$(COMPOSE) logs -f --tail=120 odoo nginx

probe:
	@echo "ACME/certbot probe is disabled for now."
	@echo "Public publishing uses Cloudflare Tunnel: make up-tunnel"
	@exit 1

certbot:
	@echo "Certbot/direct TLS mode is disabled for now."
	@echo "Supported public publish path: make up-tunnel"
	@exit 1
certbot-renew:
	@echo "Certbot renewal is disabled because certbot is not in use right now."
	@echo "Supported public publish path: make up-tunnel"
	@exit 1

db-init:
	@$(MAKE) dev-project-db-init DEV_PROJECT_DB="$(DB)"

db-check:
	@$(COMPOSE) exec -T db psql -U "$(PROD_DB_USER)" -d "$(DB)" -c "SELECT name, state FROM ir_module_module WHERE name='base';" || true

db-list:
	@./scripts/db-manager.sh list || true

db-manager:
	@./scripts/db-manager.sh

prod-db-create:
	@$(MAKE) prod-config
	@$(COMPOSE) up -d db
	@echo "Ensuring PostgreSQL database '$(PROD_DB_NAME)' exists..."
	@exists="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$(PROD_DB_NAME)'" 2>/dev/null | tr -d '[:space:]')"; \
	if [ "$$exists" = "1" ]; then \
	  echo "Production database '$(PROD_DB_NAME)' already exists."; \
	else \
	  docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d postgres -c "CREATE DATABASE \"$(PROD_DB_NAME)\" OWNER \"$(PROD_DB_USER)\""; \
	  echo "Created production database '$(PROD_DB_NAME)'."; \
	fi

prod-db-init:
	@$(MAKE) prod-config
	@$(MAKE) prod-db-create
	@echo "Checking whether Odoo schema is initialized in '$(PROD_DB_NAME)'..."
	@has_schema="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d "$(PROD_DB_NAME)" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='ir_module_module'" 2>/dev/null | tr -d '[:space:]')"; \
	if [ "$$has_schema" = "1" ]; then \
	  echo "Production database '$(PROD_DB_NAME)' already has Odoo base schema."; \
	else \
	  echo "Initializing Odoo base on fresh database '$(PROD_DB_NAME)'..."; \
	  $(COMPOSE) run --rm --no-deps odoo odoo -c /etc/odoo/odoo.conf -d "$(PROD_DB_NAME)" -i base --without-demo=True --stop-after-init; \
	  echo "Odoo base installed on '$(PROD_DB_NAME)'."; \
	fi

prod-db-ensure:
	@$(MAKE) prod-db-init

tenant-provision:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@printf '%s\n' "$(DB)" | grep -Eq '^[a-z0-9][a-z0-9-]*$$' || (echo "Invalid DB name '$(DB)'. Use lowercase letters, digits, and hyphens only."; exit 1)
	@if [ "$(DB)" = "$(PROD_DB_NAME)" ]; then echo "Refusing tenant-provision for primary DB $(PROD_DB_NAME)."; exit 1; fi
	@$(MAKE) prod-config
	@$(PROD_RUNTIME_COMPOSE) up -d db odoo nginx
	@echo "Ensuring tenant database '$(DB)' exists..."
	@exists="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$(DB)'" 2>/dev/null | tr -d '[:space:]')"; \
	if [ "$$exists" = "1" ]; then \
	  echo "Tenant database '$(DB)' already exists."; \
	else \
	  docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d postgres -c "CREATE DATABASE \"$(DB)\" OWNER \"$(PROD_DB_USER)\""; \
	  echo "Created tenant database '$(DB)'."; \
	fi
	@echo "Checking whether Odoo base schema is initialized in '$(DB)'..."
	@has_schema="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d "$(DB)" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='ir_module_module'" 2>/dev/null | tr -d '[:space:]')"; \
	modules="$(TENANT_BOOTSTRAP_MODULES)"; \
	if [ -z "$$modules" ]; then \
	  case "$(TENANT_PROFILE)" in \
	    standard) modules="$(TENANT_STANDARD_MODULES)" ;; \
	    knowledge) modules="$(TENANT_KNOWLEDGE_MODULES)" ;; \
	    gov) modules="$(TENANT_GOV_MODULES)" ;; \
	    *) echo "Unknown TENANT_PROFILE='$(TENANT_PROFILE)'. Use standard, knowledge, gov, or set TENANT_BOOTSTRAP_MODULES explicitly."; exit 1 ;; \
	  esac; \
	fi; \
	if [ "$$has_schema" = "1" ]; then \
	  echo "Tenant database '$(DB)' already has Odoo base schema."; \
	else \
	  echo "Initializing tenant database '$(DB)' with profile $(TENANT_PROFILE) and modules $$modules..."; \
	  $(PROD_RUNTIME_COMPOSE) run --rm --no-deps odoo odoo -c /etc/odoo/odoo.conf -d "$(DB)" -i "$$modules" --without-demo=True --stop-after-init; \
	  echo "Bootstrap modules ($$modules) installed on '$(DB)'."; \
	fi
	@$(MAKE) odoo-fix-url DB="$(DB)"
	@$(MAKE) tenant-bootstrap-defaults DB="$(DB)" TENANT_COMPANY_NAME="$(TENANT_COMPANY_NAME)" TENANT_ADMIN_LOGIN="$(TENANT_ADMIN_LOGIN)" TENANT_ADMIN_PASSWORD="$(TENANT_ADMIN_PASSWORD)" TENANT_ADMIN_NAME="$(TENANT_ADMIN_NAME)" TENANT_OWNER_LOGIN="$(TENANT_OWNER_LOGIN)" TENANT_OWNER_PASSWORD="$(TENANT_OWNER_PASSWORD)" TENANT_OWNER_NAME="$(TENANT_OWNER_NAME)" TENANT_CLIENT_LOGIN="$(TENANT_CLIENT_LOGIN)" TENANT_CLIENT_PASSWORD="$(TENANT_CLIENT_PASSWORD)" TENANT_CLIENT_NAME="$(TENANT_CLIENT_NAME)"
	@$(MAKE) tenant-check DB="$(DB)"
	@$(MAKE) tenant-smoke DB="$(DB)" TENANT_SMOKE_PUBLIC=0
	@echo "Tenant ready: https://$(DB).$(DOMAIN)"
	@echo "Cloudflare requirement: add Public Hostname $(DB).$(DOMAIN) -> http://nginx:80"

tenant-install-modules:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@printf '%s\n' "$(DB)" | grep -Eq '^[a-z0-9][a-z0-9-]*$$' || (echo "Invalid DB name '$(DB)'."; exit 1)
	@modules="$(TENANT_BOOTSTRAP_MODULES)"; \
	if [ -z "$$modules" ]; then \
	  case "$(TENANT_PROFILE)" in \
	    standard) modules="$(TENANT_STANDARD_MODULES)" ;; \
	    knowledge) modules="$(TENANT_KNOWLEDGE_MODULES)" ;; \
	    gov) modules="$(TENANT_GOV_MODULES)" ;; \
	    *) echo "Unknown TENANT_PROFILE='$(TENANT_PROFILE)'. Use standard, knowledge, gov, or set TENANT_BOOTSTRAP_MODULES explicitly."; exit 1 ;; \
	  esac; \
	fi; \
	echo "Installing/upgrading modules ($$modules) on tenant DB '$(DB)'..."; \
	$(PROD_RUNTIME_COMPOSE) exec -T odoo odoo -c /etc/odoo/odoo.conf -d "$(DB)" --http-port=9069 --gevent-port=9072 --stop-after-init -i "$$modules" -u "$$modules"

tenant-check: SHELL := /bin/zsh
tenant-check:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@printf '%s\n' "$(DB)" | grep -Eq '^[a-z0-9][a-z0-9-]*$$' || (echo "Invalid DB name '$(DB)'."; exit 1)
	@$(PROD_RUNTIME_COMPOSE) up -d db odoo nginx >/dev/null
	@expected_url="$$(if [ "$(DB)" = "$(PROD_DB_NAME)" ]; then printf '%s' "https://$(DOMAIN)"; else printf '%s' "https://$(DB).$(DOMAIN)"; fi)"; \
	exists="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$(DB)'" 2>/dev/null | tr -d '[:space:]')"; \
	if [ "$$exists" != "1" ]; then echo "FAIL: database '$(DB)' does not exist."; exit 1; fi; \
	base_url="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d "$(DB)" -tAc "SELECT value FROM ir_config_parameter WHERE key='web.base.url'" 2>/dev/null | tr -d '[:space:]')"; \
	if [ "$$base_url" != "$$expected_url" ]; then echo "FAIL: web.base.url is '$$base_url' but expected '$$expected_url'."; exit 1; fi; \
	freeze="$$(docker exec kodoo-db psql -U "$(PROD_DB_USER)" -d "$(DB)" -tAc "SELECT value FROM ir_config_parameter WHERE key='web.base.url.freeze'" 2>/dev/null | tr -d '[:space:]')"; \
	if [ "$$freeze" != "True" ]; then echo "FAIL: web.base.url.freeze is '$$freeze' (expected True)."; exit 1; fi; \
	login_status="$$(curl -I -s -H 'Host: $(DB).$(DOMAIN)' '$(PROD_LOCAL_HTTP_ORIGIN)/web/login?db=$(DB)' | head -n 1 | cut -d' ' -f2 | tr -d '\r')"; \
	if [ "$$login_status" != "200" ]; then echo "FAIL: tenant login endpoint returned HTTP $$login_status."; exit 1; fi; \
	root_location="$$(curl -s -I -H 'Host: $(DB).$(DOMAIN)' '$(PROD_LOCAL_HTTP_ORIGIN)/' | awk 'BEGIN{IGNORECASE=1} /^Location:/ {print $$2}' | tr -d '\r')"; \
	case "$$root_location" in \
	  *"/web/login?db=$(DB)"*) ;; \
	  *) echo "FAIL: tenant root redirect is '$$root_location'."; exit 1 ;; \
	esac; \
	root_status="$$(curl -I -s -H 'Host: $(DOMAIN)' '$(PROD_LOCAL_HTTP_ORIGIN)/' | head -n 1 | cut -d' ' -f2 | tr -d '\r')"; \
	if [ "$$root_status" != "200" ]; then echo "FAIL: primary root returned HTTP $$root_status."; exit 1; fi; \
	root_tenant_leak="$$(curl -s -I -H 'Host: $(DOMAIN)' '$(PROD_LOCAL_HTTP_ORIGIN)/' | awk 'BEGIN{IGNORECASE=1} /^Location:/ {print $$2}' | tr -d '\r')"; \
	case "$$root_tenant_leak" in \
	  *"/web/login?db="*) echo "FAIL: primary site leaked into tenant redirect '$$root_tenant_leak'."; exit 1 ;; \
	  *) ;; \
	esac; \
	echo "Tenant checks passed for DB=$(DB) ($$expected_url)."

tenant-smoke:
	@$(MAKE) guard-prod-host
	@bash ./scripts/tenant-smoke.sh "$(DB)" "$(DOMAIN)" "$(TENANT_SMOKE_PUBLIC)" "$(PROD_LOCAL_HTTP_ORIGIN)"

tenant-bootstrap-defaults:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@printf '%s\n' "$(DB)" | grep -Eq '^[a-z0-9][a-z0-9-]*$$' || (echo "Invalid DB name '$(DB)'."; exit 1)
	@base_url="$${BASE_URL:-https://$(if $(filter $(PROD_DB_NAME),$(DB)),$(DOMAIN),$(DB).$(DOMAIN))}"; \
	company_name="$(TENANT_COMPANY_NAME)"; \
	if [ -z "$$company_name" ]; then company_name="$(DB)"; fi; \
	echo "Applying tenant defaults to $(DB) ($$company_name, $$base_url)..."; \
	bash ./scripts/tenant-bootstrap-defaults.sh "$(DB)" "$$base_url" "$$company_name" "$(TENANT_ADMIN_LOGIN)" "$(TENANT_ADMIN_PASSWORD)" "$(TENANT_ADMIN_NAME)" "$(TENANT_DEFAULT_LANG)" "$(TENANT_DEFAULT_CURRENCY)" "$(TENANT_OWNER_LOGIN)" "$(TENANT_OWNER_PASSWORD)" "$(TENANT_OWNER_NAME)" "$(TENANT_CLIENT_LOGIN)" "$(TENANT_CLIENT_PASSWORD)" "$(TENANT_CLIENT_NAME)"

tenant-adjust:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@printf '%s\n' "$(DB)" | grep -Eq '^[a-z0-9][a-z0-9-]*$$' || (echo "Invalid DB name '$(DB)'."; exit 1)
	@$(MAKE) odoo-fix-url DB="$(DB)"
	@$(MAKE) tenant-bootstrap-defaults DB="$(DB)" TENANT_COMPANY_NAME="$(TENANT_COMPANY_NAME)" TENANT_ADMIN_LOGIN="$(TENANT_ADMIN_LOGIN)" TENANT_ADMIN_PASSWORD="$(TENANT_ADMIN_PASSWORD)" TENANT_ADMIN_NAME="$(TENANT_ADMIN_NAME)" TENANT_OWNER_LOGIN="$(TENANT_OWNER_LOGIN)" TENANT_OWNER_PASSWORD="$(TENANT_OWNER_PASSWORD)" TENANT_OWNER_NAME="$(TENANT_OWNER_NAME)" TENANT_CLIENT_LOGIN="$(TENANT_CLIENT_LOGIN)" TENANT_CLIENT_PASSWORD="$(TENANT_CLIENT_PASSWORD)" TENANT_CLIENT_NAME="$(TENANT_CLIENT_NAME)"
	@$(MAKE) tenant-check DB="$(DB)"
	@$(MAKE) tenant-smoke DB="$(DB)" TENANT_SMOKE_PUBLIC=0

tenant-reset:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@printf '%s\n' "$(DB)" | grep -Eq '^[a-z0-9][a-z0-9-]*$$' || (echo "Invalid DB name '$(DB)'."; exit 1)
	@if [ "$(DB)" = "$(PROD_DB_NAME)" ]; then echo "Refusing tenant-reset for primary DB $(PROD_DB_NAME)."; exit 1; fi
	@bash ./scripts/tenant-reset.sh "$(DB)" "$(PROD_DB_USER)" "$(PROD_DB_NAME)"
	@$(MAKE) tenant-provision DB="$(DB)" TENANT_PROFILE="$(TENANT_PROFILE)" TENANT_BOOTSTRAP_MODULES="$(TENANT_BOOTSTRAP_MODULES)"

tenant-user-list:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@bash ./scripts/tenant-user-list.sh "$(DB)"

tenant-user-password:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@test -n "$(LOGIN)" || (echo "Set LOGIN=<user login>."; exit 1)
	@test -n "$(PASSWORD)" || (echo "Set PASSWORD=<new password>."; exit 1)
	@bash ./scripts/tenant-user-password.sh "$(DB)" "$(LOGIN)" "$(PASSWORD)"
	@$(MAKE) tenant-user-list DB="$(DB)"

tenant-user-role:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@test -n "$(LOGIN)" || (echo "Set LOGIN=<user login or email>."; exit 1)
	@test -n "$(ROLE)" || (echo "Set ROLE=portal|internal|operator."; exit 1)
	@bash ./scripts/tenant-user-role.sh "$(DB)" "$(LOGIN)" "$(ROLE)"
	@$(MAKE) tenant-user-list DB="$(DB)"

tenant-user-create-operator:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@test -n "$(LOGIN)" || (echo "Set LOGIN=<operator email/login>."; exit 1)
	@test -n "$(NAME)" || (echo "Set NAME=<operator display name>."; exit 1)
	@test -n "$(PASSWORD)" || (echo "Set PASSWORD=<operator password>."; exit 1)
	@bash ./scripts/tenant-user-create-operator.sh "$(DB)" "$(LOGIN)" "$(NAME)" "$(PASSWORD)"
	@$(MAKE) tenant-user-list DB="$(DB)"

tenant-user-create-portal:
	@$(MAKE) guard-prod-host
	@test -n "$(DB)" || (echo "Set DB=<tenant>."; exit 1)
	@test -n "$(LOGIN)" || (echo "Set LOGIN=<portal email/login>."; exit 1)
	@test -n "$(NAME)" || (echo "Set NAME=<portal display name>."; exit 1)
	@test -n "$(PASSWORD)" || (echo "Set PASSWORD=<portal password>."; exit 1)
	@bash ./scripts/tenant-user-create-portal.sh "$(DB)" "$(LOGIN)" "$(NAME)" "$(PASSWORD)"
	@$(MAKE) tenant-user-list DB="$(DB)"

tenant-user-create-client:
	@$(MAKE) tenant-user-create-portal DB="$(DB)" LOGIN="$(LOGIN)" NAME="$(NAME)" PASSWORD="$(PASSWORD)"

root-smoke:
	@$(MAKE) guard-prod-host
	@bash ./scripts/root-smoke.sh "$(DOMAIN)" "$(PROD_LOCAL_HTTP_ORIGIN)"

odoo-tui:
	@$(MAKE) prod-config
	@$(COMPOSE) up -d odoo
	@$(COMPOSE) exec odoo bash

odoo-shell:
	@$(COMPOSE) exec odoo odoo shell -c /etc/odoo/odoo.conf -d "$(DB)"

dev-host-shell:
	@$(MAKE) guard-dev-host
	@db_name="$(strip $(DB))"; \
	if [ -z "$$db_name" ]; then db_name="$(DEV_HOST_DB)"; fi; \
	$(MAKE) dev-host-config >/dev/null; \
	"$(PYTHON)" "$(ODOO_BIN)" shell -c "$(DEV_HOST_CONFIG)" -d "$$db_name"

dev-project-shell:
	@$(MAKE) guard-dev-host
	@db_name="$(strip $(DB))"; \
	if [ -z "$$db_name" ]; then db_name="$(DEV_PROJECT_DB)"; fi; \
	$(MAKE) dev-project-config >/dev/null; \
	"$(PYTHON)" "$(ODOO_BIN)" shell -c "$(DEV_PROJECT_CONFIG)" -d "$$db_name"

odoo-fix-url:
	@$(MAKE) guard-prod-host
	@set -e; \
	base_url="$${BASE_URL:-https://$(if $(filter $(PROD_DB_NAME),$(DB)),$(DOMAIN),$(DB).$(DOMAIN))}"; \
	$(PROD_RUNTIME_COMPOSE) exec -T db psql -U "$(PROD_DB_USER)" -d "$(DB)" -c "INSERT INTO ir_config_parameter (key,value,create_uid,write_uid,create_date,write_date) VALUES ('web.base.url','$$base_url',1,1,now(),now()) ON CONFLICT (key) DO UPDATE SET value=excluded.value, write_uid=1, write_date=now();"; \
	$(PROD_RUNTIME_COMPOSE) exec -T db psql -U "$(PROD_DB_USER)" -d "$(DB)" -c "INSERT INTO ir_config_parameter (key,value,create_uid,write_uid,create_date,write_date) VALUES ('web.base.url.freeze','True',1,1,now(),now()) ON CONFLICT (key) DO UPDATE SET value=excluded.value, write_uid=1, write_date=now();"; \
	echo "Odoo base URL fixed to $$base_url for DB=$(DB)."

dev-host-db-setup:
	@PG_SERVICE="$(PG_LOCAL_SERVICE)" \
	PG_SUPERUSER="$(PG_LOCAL_SUPERUSER)" \
	APP_DB_USER="$(PG_LOCAL_USER)" \
	APP_DB_PASSWORD="$(PG_LOCAL_PASSWORD)" \
	APP_DB_NAME="$(DEV_HOST_DB)" \
	TEST_DB_NAME="$(DEV_HOST_TEST_DB)" \
	CREATE_APP_DATABASES="$(or $(DEV_HOST_PRECREATE_DATABASES),1)" \
	./scripts/dev-host-db-setup.sh

dev-host-db-init:
	@echo "Opening Odoo database manager on local PostgreSQL. Create or restore '$(DEV_HOST_DB)' at http://$(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)/web/database/manager"
	@$(MAKE) dev-host-up DEV_HOST_PRECREATE_DATABASES=0

dev-host-test-init:
	@echo "Opening Odoo database manager on local PostgreSQL. Create or restore '$(DEV_HOST_TEST_DB)' at http://$(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)/web/database/manager"
	@$(MAKE) dev-host-up DEV_HOST_PRECREATE_DATABASES=0

dev-host-up:
	@$(MAKE) guard-dev-host
	@selected_db="$(strip $(DB))"; \
	db_name="$${selected_db:-$(DEV_HOST_DB)}"; \
	precreate=0; \
	if [ -n "$$selected_db" ]; then precreate=1; fi; \
	$(MAKE) ports-clean PORTS="$(DEV_HOST_HTTP_PORT)"; \
	$(MAKE) dev-host-db-setup DEV_HOST_DB="$$db_name" DEV_HOST_PRECREATE_DATABASES="$$precreate"; \
	$(MAKE) dev-host-config; \
	PYTHON_BIN="$(PYTHON)" \
	ODOO_DEV_CONFIG="$(DEV_HOST_CONFIG)" \
	ODOO_DEV_DB="$$selected_db" \
	ODOO_DEV_LOG_PATH="$(DEV_HOST_LOG_PATH)" \
	ODOO_DEV_PID_FILE="$(DEV_HOST_PID_FILE)" \
	ODOO_DEV_HTTP_PORT="$(DEV_HOST_HTTP_PORT)" \
	./scripts/dev-host-start.sh

dev-host-stop:
	@ODOO_DEV_PID_FILE="$(DEV_HOST_PID_FILE)" ./scripts/dev-host-stop.sh

dev-host-logs:
	@mkdir -p "$$(dirname "$(DEV_HOST_LOG_PATH)")"
	@touch "$(DEV_HOST_LOG_PATH)"
	@tail -f "$(DEV_HOST_LOG_PATH)"

dev-host-status:
	@set -e; \
	if [ -f "$(DEV_HOST_PID_FILE)" ] && kill -0 "$$(cat "$(DEV_HOST_PID_FILE)")" 2>/dev/null; then \
	  echo "Odoo host dev is running with PID $$(cat "$(DEV_HOST_PID_FILE)")"; \
	  echo "URL: http://$(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)"; \
	  echo "Database manager: http://$(LOCAL_BIND_HOST):$(DEV_HOST_HTTP_PORT)/web/database/manager"; \
	else \
	  echo "Odoo host dev is not running."; \
	fi; \
	if command -v systemctl >/dev/null 2>&1; then \
	  systemctl is-active "$(PG_LOCAL_SERVICE)" >/dev/null 2>&1 && echo "PostgreSQL service $(PG_LOCAL_SERVICE): active" || echo "PostgreSQL service $(PG_LOCAL_SERVICE): inactive"; \
	fi

dev-host-upgrade:
	@$(MAKE) dev-host-db-setup
	@$(MAKE) dev-host-config
	@$(PYTHON) $(ODOO_BIN) -c "$(DEV_HOST_CONFIG)" -d "$(DEV_UPGRADE_DB)" -u "$(DEV_MODULES)" --stop-after-init

dev-project-db-setup:
	@echo "WARNING: dev-project-db-setup shares the Docker DB service from the compose stack."
	@COMPOSE_BIN='$(COMPOSE_PROJECT_DB)' \
	DB_USER="$(PROD_DB_USER)" \
	DB_PASSWORD="$(PROD_DB_PASSWORD)" \
	DB_NAME="$(DEV_PROJECT_DB)" \
	CREATE_APP_DATABASE="$(or $(DEV_PROJECT_PRECREATE_DATABASE),1)" \
	./scripts/dev-project-db-setup.sh

dev-project-db-init:
	@echo "Opening Odoo database manager over Docker PostgreSQL. Create or restore '$(DEV_PROJECT_DB)' at http://$(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT)/web/database/manager"
	@$(MAKE) dev-project-up DEV_PROJECT_PRECREATE_DATABASE=0

dev-project:
	@$(MAKE) dev-project-up

dev-project-up:
	@$(MAKE) guard-dev-host
	@echo "WARNING: dev-project-up shares the Docker DB service. Avoid while the public tunnel stack is serving traffic."
	@selected_db="$(strip $(DB))"; \
	db_name="$${selected_db:-$(DEV_PROJECT_DB)}"; \
	precreate=0; \
	if [ -n "$$selected_db" ]; then precreate=1; fi; \
	$(MAKE) ports-clean PORTS="$(DEV_PROJECT_HTTP_PORT)"; \
	$(MAKE) dev-project-db-setup DEV_PROJECT_DB="$$db_name" DEV_PROJECT_PRECREATE_DATABASE="$$precreate"; \
	$(MAKE) dev-project-config; \
	PYTHON_BIN="$(PYTHON)" \
	ODOO_DEV_CONFIG="$(DEV_PROJECT_CONFIG)" \
	ODOO_DEV_DB="$$selected_db" \
	ODOO_DEV_LOG_PATH="$(DEV_PROJECT_LOG_PATH)" \
	ODOO_DEV_PID_FILE="$(DEV_PROJECT_PID_FILE)" \
	ODOO_DEV_HTTP_PORT="$(DEV_PROJECT_HTTP_PORT)" \
	./scripts/dev-host-start.sh

dev-project-stop:
	@ODOO_DEV_PID_FILE="$(DEV_PROJECT_PID_FILE)" ./scripts/dev-host-stop.sh >/dev/null 2>&1 || true
	@$(COMPOSE_PROJECT_DB) stop db >/dev/null 2>&1 || true

dev-project-logs:
	@mkdir -p "$$(dirname "$(DEV_PROJECT_LOG_PATH)")"
	@touch "$(DEV_PROJECT_LOG_PATH)"
	@tail -f "$(DEV_PROJECT_LOG_PATH)"

dev-project-status:
	@set -e; \
	if [ -f "$(DEV_PROJECT_PID_FILE)" ] && kill -0 "$$(cat "$(DEV_PROJECT_PID_FILE)")" 2>/dev/null; then \
	  echo "Project mode Odoo is running with PID $$(cat "$(DEV_PROJECT_PID_FILE)")"; \
	  echo "URL: http://$(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT)"; \
	  echo "Database manager: http://$(LOCAL_BIND_HOST):$(DEV_PROJECT_HTTP_PORT)/web/database/manager"; \
	else \
	  echo "Project mode Odoo is not running."; \
	fi; \
	docker inspect -f '{{.State.Status}}' kodoo-db 2>/dev/null | sed 's/^/Docker PostgreSQL: /' || echo "Docker PostgreSQL: not running"; \
	echo "Database: $(DEV_PROJECT_DB) via $(DOCKER_DB_BIND_HOST):$(DOCKER_DB_HOST_PORT)"

dev-host-backup:
	@BACKUP_DIR="$(BACKUP_DIR)" \
	DB_HOST="$(PG_LOCAL_HOST)" \
	DB_PORT="$(PG_LOCAL_PORT)" \
	APP_DB_USER="$(PG_LOCAL_USER)" \
	APP_DB_PASSWORD="$(PG_LOCAL_PASSWORD)" \
	APP_DB_NAME="$(DEV_HOST_DB)" \
	./scripts/dev-host-backup.sh

dev-host-restore-ktest:
	@$(MAKE) dev-host-db-setup
	@BACKUP_DIR="$(BACKUP_DIR)" \
	DB_HOST="$(PG_LOCAL_HOST)" \
	DB_PORT="$(PG_LOCAL_PORT)" \
	APP_DB_USER="$(PG_LOCAL_USER)" \
	APP_DB_PASSWORD="$(PG_LOCAL_PASSWORD)" \
	TEST_DB_NAME="$(DEV_HOST_TEST_DB)" \
	./scripts/dev-host-restore-ktest.sh

assets-rebuild:
	@$(MAKE) guard-prod-host
	@echo "Clearing cached web assets from database ($(DB))..."
	@$(COMPOSE) exec -T db psql -U "$(PROD_DB_USER)" -d "$(DB)" -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';"
	@echo "Restarting Odoo to regenerate bundles..."
	@$(COMPOSE) restart odoo
	@echo "Assets reset complete. Do a hard refresh in browser (Ctrl+F5)."

assets-reset:
	@$(MAKE) guard-prod-host
	@echo "Hard resetting Odoo assets (DB + Upgrade force)..."
	@$(COMPOSE) exec -T db psql -U "$(PROD_DB_USER)" -d "$(DB)" -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%' OR name LIKE 'web.assets_%';"
	@echo "Marking 'web' module for upgrade to force total bundle regeneration..."
	@$(COMPOSE) exec -T db psql -U "$(PROD_DB_USER)" -d "$(DB)" -c "UPDATE ir_module_module SET state='to upgrade' WHERE name='web';"
	@echo "Restarting Odoo..."
	@$(COMPOSE) restart odoo
	@echo "Assets hard reset complete. The next page load will take longer while bundles are regenerated."
	@echo "Assets reset complete. Do a hard refresh in browser (Ctrl+F5)."

smoke:
	@$(MAKE) guard-prod-host
	@set -e; \
	echo "== Smoke check ($(DOMAIN)) =="; \
	$(COMPOSE) ps >/dev/null; \
	for svc in db odoo nginx; do \
	  running="$$(docker inspect -f '{{.State.Running}}' kodoo-$$svc 2>/dev/null || true)"; \
	  if [ "$$running" != "true" ]; then \
	    echo "FAIL: service '$$svc' is not running."; \
	    exit 1; \
	  fi; \
	done; \
	echo "OK: required services are running."; \
	local_base=""; \
	local_code=""; \
	for base in "http://$(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT)" "http://127.0.0.1" "https://127.0.0.1"; do \
	  curl_flags=""; \
	  case "$$base" in https://*) curl_flags="-k" ;; esac; \
	  code="$$(curl $$curl_flags -sS -o /dev/null -w '%{http_code}' "$$base/odoo" || true)"; \
	  if [ "$$code" = "200" ] || [ "$$code" = "303" ]; then \
	    local_base="$$base"; \
	    local_code="$$code"; \
	    break; \
	  fi; \
	done; \
	if [ -z "$$local_base" ]; then \
	  echo "FAIL: local endpoint unreachable. Tried: http://$(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT)/odoo, http://127.0.0.1/odoo, https://127.0.0.1/odoo"; \
	  exit 1; \
	fi; \
	echo "OK: local endpoint $$local_base/odoo HTTP $$local_code."; \
	ws_curl_flags=""; \
	case "$$local_base" in https://*) ws_curl_flags="-k" ;; esac; \
	ws_health_code="$$(curl $$ws_curl_flags -sS -o /dev/null -w '%{http_code}' \
	  -H 'Host: $(DOMAIN)' \
	  "$$local_base/websocket/health" || true)"; \
	if [ "$$ws_health_code" != "200" ]; then \
	  echo "FAIL: websocket health endpoint ($$local_base/websocket/health) returned HTTP $$ws_health_code (expected 200)."; \
	  exit 1; \
	fi; \
	echo "OK: websocket health endpoint HTTP $$ws_health_code."; \
	if [ "$(SMOKE_PUBLIC)" = "1" ]; then \
	  public_code="$$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://$(DOMAIN) || true)"; \
	  if [ "$$public_code" != "200" ] && [ "$$public_code" != "301" ] && [ "$$public_code" != "302" ] && [ "$$public_code" != "303" ]; then \
	    cloudflared_running="$$(docker inspect -f '{{.State.Running}}' kodoo-cloudflared 2>/dev/null || true)"; \
	    echo "FAIL: public endpoint https://$(DOMAIN) returned HTTP $$public_code."; \
	    www_code="$$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://www.$(DOMAIN) || true)"; \
	    if [ "$$www_code" = "200" ] || [ "$$www_code" = "301" ] || [ "$$www_code" = "302" ] || [ "$$www_code" = "303" ]; then \
	      echo "Hint: https://www.$(DOMAIN) resolves, but apex https://$(DOMAIN) does not. Publish the apex hostname in Cloudflare."; \
	    fi; \
	    if [ "$$cloudflared_running" != "true" ]; then \
	      echo "Hint: domain may be pointing to Cloudflare Tunnel, but 'kodoo-cloudflared' is not running."; \
	      echo "Run: fill CLOUDFLARED_TOKEN in .env, then use make up-tunnel."; \
	    else \
	      public_body="$$(curl -sS --max-time 20 https://$(DOMAIN) || true)"; \
	      if printf '%s' "$$public_body" | grep -q 'error code: 1016'; then \
	        echo "Hint: Cloudflare returned error 1016 (origin/tunnel resolution failure)."; \
	        echo "Check Cloudflare Zero Trust > Tunnels > Public Hostnames:"; \
	        echo "  $(DOMAIN) -> http://nginx:80"; \
	        echo "Also remove conflicting direct A/AAAA/CNAME records for $(DOMAIN) in Cloudflare DNS."; \
	      fi; \
	    fi; \
	    exit 1; \
	  fi; \
	  echo "OK: public endpoint HTTP $$public_code."; \
	else \
		echo "Skipping public endpoint check (SMOKE_PUBLIC=0)."; \
	fi; \
	echo "Smoke check passed."

troubleshoot:
	@$(MAKE) guard-prod-host
	@set +e; \
	rc=0; \
	echo "== Troubleshoot ($(DOMAIN)) =="; \
	echo ""; \
	echo "== Files =="; \
	if [ -f .env ] || [ -f .env.make ]; then echo "OK: env file found."; else echo "FAIL: .env/.env.make missing."; rc=1; fi; \
	if [ -f "$(PROD_CONFIG)" ]; then echo "OK: $(PROD_CONFIG) found."; else echo "WARN: $(PROD_CONFIG) missing. Run: make prod-config"; fi; \
	if [ -f "$(DEV_HOST_CONFIG)" ]; then echo "OK: $(DEV_HOST_CONFIG) found."; else echo "INFO: $(DEV_HOST_CONFIG) not present."; fi; \
	echo ""; \
	echo "== Services =="; \
	$(COMPOSE) ps || rc=1; \
	echo ""; \
	echo "== Local HTTP =="; \
	local_base=""; \
	local_code=""; \
	for base in "http://$(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT)" "http://127.0.0.1" "https://127.0.0.1"; do \
	  curl_flags=""; \
	  case "$$base" in https://*) curl_flags="-k" ;; esac; \
	  code="$$(curl $$curl_flags -sS -o /dev/null -w '%{http_code}' "$$base/odoo" || true)"; \
	  echo "$$base/odoo -> $$code"; \
	  if [ "$$code" = "200" ] || [ "$$code" = "303" ]; then \
	    local_base="$$base"; \
	    local_code="$$code"; \
	  fi; \
	done; \
	if [ -z "$$local_base" ]; then \
	  echo "FAIL: no local endpoint answered with 200/303."; \
	  rc=1; \
	else \
	  echo "OK: using local base $$local_base (HTTP $$local_code)."; \
	fi; \
	echo ""; \
	echo "== Websocket =="; \
	if [ -n "$$local_base" ]; then \
	  ws_curl_flags=""; \
	  case "$$local_base" in https://*) ws_curl_flags="-k" ;; esac; \
	  ws_health_code="$$(curl $$ws_curl_flags -sS -o /dev/null -w '%{http_code}' \
	    -H 'Host: $(DOMAIN)' \
	    "$$local_base/websocket/health" || true)"; \
	  echo "$$local_base/websocket/health -> $$ws_health_code"; \
	  if [ "$$ws_health_code" != "200" ]; then \
	    echo "FAIL: websocket health probe returned $$ws_health_code."; \
	    rc=1; \
	  fi; \
	else \
	  echo "SKIP: websocket probe skipped because no local endpoint passed."; \
	fi; \
	echo ""; \
	if [ "$(SMOKE_PUBLIC)" = "1" ]; then \
	  echo "== Public HTTP =="; \
	  public_code="$$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://$(DOMAIN) || true)"; \
	  echo "https://$(DOMAIN) -> $$public_code"; \
	  if [ "$$public_code" != "200" ] && [ "$$public_code" != "301" ] && [ "$$public_code" != "302" ] && [ "$$public_code" != "303" ]; then \
	    echo "FAIL: public endpoint check failed."; \
	    www_code="$$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://www.$(DOMAIN) || true)"; \
	    echo "https://www.$(DOMAIN) -> $$www_code"; \
	    if [ "$$www_code" = "200" ] || [ "$$www_code" = "301" ] || [ "$$www_code" = "302" ] || [ "$$www_code" = "303" ]; then \
	      echo "INFO: www resolves, but apex $(DOMAIN) does not. Publish the apex hostname in Cloudflare."; \
	    fi; \
	    rc=1; \
	  fi; \
	  cloudflared_running="$$(docker inspect -f '{{.State.Running}}' kodoo-cloudflared 2>/dev/null || true)"; \
	  if [ "$$cloudflared_running" = "true" ]; then \
	    echo "INFO: cloudflared container is running."; \
	  else \
	    echo "INFO: cloudflared container is not running."; \
	  fi; \
	  if [ "$$public_code" != "200" ] && [ "$$public_code" != "301" ] && [ "$$public_code" != "302" ] && [ "$$public_code" != "303" ]; then \
	    public_body="$$(curl -sS --max-time 20 https://$(DOMAIN) || true)"; \
	    if printf '%s' "$$public_body" | grep -q 'error code: 1016'; then \
	      echo "INFO: Cloudflare error 1016 detected."; \
	      echo "INFO: Check Zero Trust Public Hostname $(DOMAIN) -> http://nginx:80"; \
	      echo "INFO: Remove conflicting direct DNS records for $(DOMAIN)."; \
	    fi; \
	  fi; \
	  echo ""; \
	fi; \
	echo "== Hints =="; \
	echo "make logs"; \
	echo "make logs-local"; \
	echo "make logs-tunnel"; \
	echo "make down && make up          # local/home stack"; \
	echo "make down-tunnel && make up-tunnel   # public internet path"; \
	exit $$rc

tui: tui-build
	@TUI_REFRESH_SECONDS="$(TUI_REFRESH_SECONDS)" TUI_LOG_LINES="$(TUI_LOG_LINES)" "$(KODOO_TUI_BIN)"

tui-live: tui

tui-build:
	@if ! command -v "$(GO)" >/dev/null 2>&1; then \
	  echo "Missing Go toolchain: $(GO)"; \
	  echo "Install Go 1.22+ or override with: make tui-build GO=go"; \
	  exit 1; \
	fi
	@mkdir -p "$(dir $(KODOO_TUI_BIN))"
	@cd "$(KODOO_TUI_DIR)" && "$(GO)" build -o "./bin/kodoo-tui" ./cmd/kodoo-tui
	@echo "Built $(KODOO_TUI_BIN)."

tui-install:
	@if ! command -v "$(GO)" >/dev/null 2>&1; then \
	  echo "Missing Go toolchain: $(GO)"; \
	  echo "Install Go 1.22+ or override with: make tui-install GO=go"; \
	  exit 1; \
	fi
	@cd "$(KODOO_TUI_DIR)" && "$(GO)" mod download
	@$(MAKE) tui-build
	@echo "Go TUI ready at $(KODOO_TUI_BIN)."
	@echo "Run: make tui"

tui-menu:
	@./scripts/make-tui.sh

tui-doctor:
	@echo "== TUI runtime =="; \
	if command -v "$(GO)" >/dev/null 2>&1; then \
	  echo "go: $$("$(GO)" version 2>/dev/null)"; \
	else \
	  echo "go: missing ($(GO))"; \
	fi; \
	if [ -x "$(KODOO_TUI_BIN)" ]; then \
	  echo "binary: $(KODOO_TUI_BIN)"; \
	else \
	  echo "binary: not built"; \
	fi; \
	if [ -f .env ]; then echo ".env: present"; elif [ -f .env.make ]; then echo ".env.make: present (legacy)"; else echo ".env: missing"; fi; \
	if command -v docker >/dev/null 2>&1; then \
	  echo "docker cli: ok"; \
	  docker_check="$$(docker version 2>&1 || true)"; \
	  if [ -S /var/run/docker.sock ] && docker version >/dev/null 2>&1; then \
	    echo "docker daemon: ok"; \
	  elif printf '%s' "$$docker_check" | grep -q "could not be found in this WSL 2 distro"; then \
	    echo "docker daemon: WSL integration disabled for this distro"; \
	  elif printf '%s' "$$docker_check" | grep -qi "permission denied"; then \
	    echo "docker daemon: permission denied"; \
	  elif printf '%s' "$$docker_check" | grep -qi "Cannot connect to the Docker daemon"; then \
	    echo "docker daemon: not reachable"; \
	  else \
	    echo "docker daemon: unavailable"; \
	  fi; \
	else echo "docker cli: missing"; echo "docker daemon: unavailable"; fi; \
	if command -v curl >/dev/null 2>&1; then echo "curl: ok"; else echo "curl: missing"; fi

up-smoke:
	@$(MAKE) up-tunnel
	@$(MAKE) smoke

mobile-install:
	@cd "$(MOBILE_DIR)" && npm install

mobile-doctor:
	@cd "$(MOBILE_DIR)" && npm run doctor

mobile-add-android:
	@cd "$(MOBILE_DIR)" && npm run add:android

mobile-add-ios:
	@cd "$(MOBILE_DIR)" && npm run add:ios

mobile-sync:
	@cd "$(MOBILE_DIR)" && npm run sync

mobile-open-android:
	@cd "$(MOBILE_DIR)" && npm run open:android

mobile-open-ios:
	@cd "$(MOBILE_DIR)" && npm run open:ios

ollama-pull:
	@$(COMPOSE) up -d ollama
	@$(COMPOSE) exec -e OLLAMA_MODEL="$(OLLAMA_MODEL)" ollama sh -c 'until ollama list >/dev/null 2>&1; do sleep 2; done; echo "Pulling $$OLLAMA_MODEL"; ollama pull "$$OLLAMA_MODEL"'

ollama-list:
	@$(COMPOSE) exec ollama ollama list

up-insecure:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(INSECURE_HTTP_PORT) $(INSECURE_EVENTED_PORT)"
	@$(MAKE) prod-db-ensure
	@echo "WARNING: insecure mode enabled (no TLS/reverse-proxy protections)."
	@$(COMPOSE) stop nginx >/dev/null 2>&1 || true
	@$(COMPOSE_INSECURE) up -d db odoo ollama
	@$(MAKE) ollama-pull
	@echo "Odoo exposed on port $(INSECURE_HTTP_PORT) (evented: $(INSECURE_EVENTED_PORT))."

down-insecure:
	@$(COMPOSE_INSECURE) down --remove-orphans

up-cloudflare:
	@echo "Cloudflare DNS proxy / full-connection mode is disabled for now."
	@echo "Use Cloudflare Tunnel instead: make up-tunnel"
	@exit 1

logs-cloudflare:
	@echo "Legacy direct Cloudflare mode is disabled."
	@echo "Use make logs-tunnel for the supported public path."
	@exit 1

down-cloudflare:
	@echo "Stopping any legacy direct Cloudflare stack if it exists."
	@$(COMPOSE) down --remove-orphans

up-tunnel:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(LOCAL_HTTP_PORT)"
	@test -n "$(CLOUDFLARED_TOKEN)" || (echo "Set CLOUDFLARED_TOKEN in .env first."; exit 1)
	@$(MAKE) prod-db-ensure
	@$(COMPOSE_TUNNEL) up -d db odoo nginx ollama cloudflared
	@$(MAKE) ollama-pull
	@echo "Cloudflare tunnel mode started."
	@echo "This is the default public internet publishing path."
	@echo "Local:  http://$(LOCAL_BIND_HOST):$(LOCAL_HTTP_PORT)"
	@echo "Public: https://$(DOMAIN)"
	@echo "Multi-tenant note: with PROD_DBFILTER=$(PROD_DBFILTER), each tenant also needs a public hostname like https://<db>.$(DOMAIN)"

logs-tunnel:
	@$(COMPOSE_TUNNEL) logs -f --tail=120 cloudflared nginx odoo

down-tunnel:
	@$(COMPOSE_TUNNEL) down --remove-orphans

up-lean-tunnel:
	@$(MAKE) guard-prod-host
	@$(MAKE) prod-config
	@$(MAKE) ports-clean PORTS="$(LOCAL_HTTP_PORT) 80"
	@test -n "$(CLOUDFLARED_TOKEN)" || (echo "Set CLOUDFLARED_TOKEN in .env first."; exit 1)
	@$(MAKE) prod-db-ensure
	@$(COMPOSE_LEAN_TUNNEL) up -d db odoo nginx ollama cloudflared
	@$(MAKE) ollama-pull
	@echo "Lean Tunnel mode started."
	@echo "Local Odoo:  http://$(LOCAL_BIND_HOST):8069"
	@echo "Local Nginx: http://$(LOCAL_BIND_HOST):80"
	@echo "Public:      https://$(DOMAIN)"
	@echo "Multi-tenant note: with PROD_DBFILTER=$(PROD_DBFILTER), each tenant also needs a public hostname like https://<db>.$(DOMAIN)"

logs-lean-tunnel:
	@$(COMPOSE_LEAN_TUNNEL) logs -f --tail=120 cloudflared nginx odoo

down-lean-tunnel:
	@$(COMPOSE_LEAN_TUNNEL) down --remove-orphans

tunnel-check:
	@test -n "$(SUBDOMAIN)" || (echo "Set SUBDOMAIN=<tenant>."; exit 1)
	@host="$(SUBDOMAIN).$(DOMAIN)"; \
	echo "== Tunnel check for $$host =="; \
	root_code="$$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://$(DOMAIN) || true)"; \
	sub_code="$$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://$$host || true)"; \
	echo "https://$(DOMAIN) -> $$root_code"; \
	echo "https://$$host -> $$sub_code"; \
	if [ "$$sub_code" = "000" ]; then \
	  echo "FAIL: $$host does not resolve or is not routed by Cloudflare Tunnel."; \
	  echo "Add a Public Hostname or wildcard (*. $(DOMAIN) without the space) pointing to http://nginx:80."; \
	  exit 1; \
	fi; \
	if [ "$$sub_code" -ge 400 ]; then \
	  echo "WARN: $$host reached the tunnel but returned HTTP $$sub_code."; \
	  echo "Check Odoo dbfilter, tenant DB existence, and web.base.url for DB=$(SUBDOMAIN)."; \
	  exit 1; \
	fi; \
	echo "OK: $$host is publicly reachable."

clean:
	@echo "Cleaning Python cache and logs..."
	@find . -name "__pycache__" -type d -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@rm -rf logs/*.log logs/*.pid
	@echo "Basic clean complete."

clean-all: clean
	@echo "Performing deep clean..."
	@rm -rf node_modules/
	@rm -rf .venv-tui/
	@rm -rf mobile/kodoo-capacitor/node_modules/
	@rm -rf mobile/kodoo-capacitor/android/.gradle/
	@rm -rf mobile/kodoo-capacitor/android/app/build/
	@rm -rf mobile/kodoo-capacitor/android/build/
	@rm -rf mobile/kodoo-capacitor/ios/App/App/public/
	@echo "Deep clean complete. Reinstall dependencies with 'make deps-install' or 'make tui-install'."
## dev-host-stop: encerra o processo nativo Odoo dev-host e remove o PID file
dev-host-stop:
	@if [ -f logs/odoo-dev-host.pid ]; then \
		pid=$$(cat logs/odoo-dev-host.pid); \
		if kill -0 "$$pid" 2>/dev/null; then \
			kill "$$pid" && echo "dev-host (pid $$pid) encerrado."; \
		else \
			echo "dev-host: processo $$pid não estava rodando."; \
		fi; \
		rm -f logs/odoo-dev-host.pid; \
	else \
		echo "dev-host: nenhum PID file encontrado."; \
	fi

## dev-project-stop: encerra o processo nativo Odoo dev-project e remove o PID file
dev-project-stop:
	@if [ -f logs/odoo-dev-project.pid ]; then \
		pid=$$(cat logs/odoo-dev-project.pid); \
		if kill -0 "$$pid" 2>/dev/null; then \
			kill "$$pid" && echo "dev-project (pid $$pid) encerrado."; \
		else \
			echo "dev-project: processo $$pid não estava rodando."; \
		fi; \
		rm -f logs/odoo-dev-project.pid; \
	else \
		echo "dev-project: nenhum PID file encontrado."; \
