from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cz_scheme_code = fields.Selection(
        selection=[
            ('0', "0 - Standard VAT regime"),
            ('1', "1 - Section 89 of VAT Act special scheme for a travel service"),
            ('2', "2 - Section 90 of VAT Act margin scheme"),
        ],
        string="Special scheme code",
        help="Code indicating special scheme, optionally used for VAT control report.",
        default='0',
    )
