from odoo import SUPERUSER_ID, api

from odoo.addons.integration.tools.connection_migration import (
    connect_bound_credentials,
)


def migrate(cr, version):
    if not version:
        return
    connect_bound_credentials(api.Environment(cr, SUPERUSER_ID, {}))
