from odoo import fields, models


class L10nTrNilveraAlias(models.Model):
    _inherit = 'l10n_tr.nilvera.alias'

    global_user_type = fields.Selection(
        selection=[
            ('Invoice', "e-Invoice"),
            ('DespatchAdvice', "e-Dispatch"),
        ],
        string="Nilvera Global User Type",
    )
