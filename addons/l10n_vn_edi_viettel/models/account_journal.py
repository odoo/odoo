# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_vn_edi_default_symbol_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='Default E-invoice Symbol',
        help='Used for only this Journal. Leave it blank to use global default symbol.',
    )
