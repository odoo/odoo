# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ar_withholding_ids = fields.One2many(
        'account.move.line', 'move_id', string='Withholdings',
        compute='_compute_l10n_ar_withholding_ids',
        readonly=True
    )

    @api.depends('line_ids')
    def _compute_l10n_ar_withholding_ids(self):
        for move in self:
            move.l10n_ar_withholding_ids = move.line_ids.filtered(lambda l: l.tax_line_id.l10n_ar_withholding_payment_type)

    def _get_tax_factor(self):
        """
        Calculate and return the tax factor for the current account move.

        The tax factor is determined based on the ratio of the untaxed amount
        to the total amount. If the total amount is zero, a default tax factor
        of 1.0 is used. Additionally, if the document type letter is 'B' and
        the tax factor is 1.0, the tax factor is adjusted to account for a
        21% VAT exemption.

        Returns:
            float: The calculated tax factor.
        """
        self.ensure_one()
        tax_factor = self.amount_total and (self.amount_untaxed / self.amount_total) or 1.0
        doc_letter = self.l10n_latam_document_type_id.l10n_ar_letter
        # if we receive B invoices, then we take out 21 of vat
        # this use of case if when company is except on vat for eg.
        if tax_factor == 1.0 and doc_letter == 'B':
            tax_factor = 1.0 / 1.21
        return tax_factor
