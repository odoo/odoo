# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    preferred_payment_method_id = fields.Many2one(
        string="Preferred Payment Method",
        comodel_name='account.payment.method',
        compute='_compute_preferred_payment_method_idd',
        store=True,
    )

    @api.depends('partner_id')
    def _compute_preferred_payment_method_idd(self):
        for move in self:
            partner = move.partner_id
            # take the payment method corresponding to the move's company
            move.preferred_payment_method_id = partner.with_company(move.company_id).property_payment_method_id
