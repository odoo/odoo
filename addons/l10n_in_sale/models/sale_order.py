# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_in_reseller_partner_id = fields.Many2one('res.partner',
        string='Reseller', domain=[('vat', '!=', False)], states={'posted': [('readonly', True)]})
    l10n_in_unit_id = fields.Many2one(
        'res.partner',
        string="Operating Unit",
        ondelete="restrict",
        default=lambda self: self.env.user._get_default_unit())


    @api.onchange('company_id')
    def _onchange_company_id(self):
        default_unit = self.l10n_in_unit_id or self.env.user._get_default_unit()
        if default_unit not in self.company_id.l10n_in_unit_ids:
            self.l10n_in_unit_id = self.company_id.partner_id

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['l10n_in_reseller_partner_id'] = self.l10n_in_reseller_partner_id.id
        invoice_vals['l10n_in_unit_id'] = self.l10n_in_unit_id.id
        return invoice_vals
