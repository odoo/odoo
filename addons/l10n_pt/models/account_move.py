# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_pt_tax_exemption_reason = fields.Many2one(
        string="Tax exemption reason",
        related='product_id.l10n_pt_tax_exemption_reason',
        help="Reason why we may exempt an item sale from any tax",
        groups='account.group_account_invoice')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        super()._onchange_product_id()
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.l10n_pt_tax_exemption_reason = line._get_computed_tax_exemption_reason()

    def _get_computed_tax_exemption_reason(self):
        self.ensure_one()

        if not self.product_id:
            return

        if not self.product_id.l10n_pt_tax_exemption_reason:
            return

        return self.product_id.l10n_pt_tax_exemption_reason


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        for move in self:
            for line in move.line_ids:
                for tax in line.tax_ids:
                    if float_is_zero(tax.amount, precision_digits=2) and not line.l10n_pt_tax_exemption_reason:
                        raise UserError(_("A tax exemption reason must be filled for the lines with a VAT amount equal to zero."))
        super().action_post()
