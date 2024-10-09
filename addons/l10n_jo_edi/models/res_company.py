from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jo_edi_client_id = fields.Char("Jordan EINV Client ID")
    l10n_jo_edi_secret_key = fields.Char("Jordan EINV Secret Key")
    l10n_jo_edi_sequence_income_source = fields.Char("Sequence of Income Source")
    l10n_jo_edi_taxpayer_type = fields.Selection(
        selection=[
            ('income', "Unregistered in the sales tax"),
            ('sales', "Registered in the sales tax"),
            ('special', "Registered in the special sales tax"),
        ],
        default='income',
        required=True,
    )
