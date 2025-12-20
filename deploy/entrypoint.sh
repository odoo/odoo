#!/usr/bin/env bash
set -euo pipefail

# Ajusta perms (útil quando PV/hostPath vem root:root)
chown -R odoo:odoo /var/lib/odoo /mnt/extra-addons /etc/odoo || true

exec gosu odoo "$@"