# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_br_invoice_serial = fields.Char(
        'Series', copy=False,
        help='Brazil: Series number associated with this Journal. If more than one Series needs to be used, duplicate this Journal and assign the new Series to the duplicated Journal.'
    )

    @api.depends('l10n_br_invoice_serial')
    def _compute_display_name(self):
        res = super()._compute_display_name()
        for journal in self.filtered('l10n_br_invoice_serial'):
            journal.display_name = f'{journal.l10n_br_invoice_serial}-{journal.display_name}'

        return res
