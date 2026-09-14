from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        UPDATE website
           SET plausible_shared_key_set = COALESCE(plausible_shared_key, '') != ''
        """
    )
    env["website"]._move_columns_into_credentials(["plausible_shared_key"])
