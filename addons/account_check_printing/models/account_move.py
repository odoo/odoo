# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):
    _inherit = 'account.move'

    preferred_payment_method_id = fields.Many2one(
        string="Preferred Payment Method",
        comodel_name='account.payment.method',
        compute='_compute_preferred_payment_method_idd',
        store=True,
    )

    def _auto_init(self):
        """ Create column for `preferred_payment_method_id` to avoid having it
        computed by the ORM on installation. Since `property_payment_method_id` is
        introduced in this module, there is no need for UPDATE
        """
        if not column_exists(self.env.cr, "account_move", "preferred_payment_method_id"):
            create_column(self.env.cr, "account_move", "preferred_payment_method_id", "int4")
        return super()._auto_init()

    @api.depends('partner_id')
    def _compute_preferred_payment_method_idd(self):
        for move in self:
            partner = move.partner_id
            # take the payment method corresponding to the move's company
            move.preferred_payment_method_id = partner.with_company(move.company_id).property_payment_method_id
