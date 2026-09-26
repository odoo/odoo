from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_vn_default_invoice_symbol_id = fields.Many2one(
        comodel_name='l10n_vn.symbol',
        string='Default E-Invoice Symbol',
        help='Used only for this journal. Leave it blank to use the global default symbol.',
        check_company=True,
        domain=[('usage', '=', 'invoice')],
    )
