"""Rename provider_openerp → provider_odoo XML ID."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'provider_odoo'
         WHERE module = 'auth_oauth'
           AND name = 'provider_openerp'
        """
    )
