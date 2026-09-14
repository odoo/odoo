from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company.ldap"]._move_columns_into_credentials(["ldap_password"])
