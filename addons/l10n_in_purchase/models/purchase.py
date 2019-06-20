
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.purchase.models.purchase import PurchaseOrder


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit", ondelete="restrict", states=PurchaseOrder.READONLY_STATES, default=lambda self: self.env.user._get_default_unit())

    def action_view_invoice(self):
        result = super(PurchaseOrder, self).action_view_invoice()
        result['context']['default_l10n_in_unit_id'] = self.l10n_in_unit_id.id
        return result

    @api.onchange('company_id')
    def _onchange_company_id(self):
        default_unit = self.l10n_in_unit_id or self.env.user._get_default_unit()
        if default_unit not in self.company_id.l10n_in_unit_ids:
            self.l10n_in_unit_id = self.company_id.partner_id
