from odoo.addons.integration.tools.ingress_adoption import (
    adopt_ingress_from_credential,
)


def migrate(cr, version):
    if not version:
        return
    adopt_ingress_from_credential(cr)
