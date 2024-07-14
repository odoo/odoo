# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Amazon invoices are made simplified by default, as currently it is not possible
    # to get the vat number from the amazon api.
    # As the invoice, if standard, will likely fail when sending it to the SII due to
    # the lack of informations about the customer.
    def _compute_l10n_es_is_simplified(self):
        super()._compute_l10n_es_is_simplified()
        for move in self:
            if any(move.invoice_line_ids.sale_line_ids.mapped('amazon_item_ref')):
                move.l10n_es_is_simplified = True
