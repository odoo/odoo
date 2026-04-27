from odoo import fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    l10n_it_sia_code = fields.Char(
        string='SIA code',
        help="Identifier used in Italy for interbank transactions"
             " by the Società Interbancaria per l'Automazione"
    )
