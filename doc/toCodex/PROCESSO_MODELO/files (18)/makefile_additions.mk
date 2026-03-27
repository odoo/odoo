# ─────────────────────────────────────────────────────────────────────────────
# Targets para encerrar processos nativos dev-host e dev-project.
# Adicionar perto dos outros targets dev-* no Makefile existente.
# ─────────────────────────────────────────────────────────────────────────────

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
	fi

# ─────────────────────────────────────────────────────────────────────────────
# Correção de versão Go (procure o comentário "Install Go 1.22+" no Makefile
# e atualize para "Install Go 1.24+").
#
# A linha atual está em torno de Makefile:1455:
#   @echo "Install Go 1.22+"
# Deve ser:
#   @echo "Install Go 1.24+"
#
# O go.mod declara 'go 1.24.0' — o comentário no Makefile é o que estava
# desatualizado.
# ─────────────────────────────────────────────────────────────────────────────
