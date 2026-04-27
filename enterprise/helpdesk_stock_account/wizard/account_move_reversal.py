# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.osv import expression


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    product_id = fields.Many2one(related='helpdesk_ticket_id.product_id', readonly=False)
    lot_id = fields.Many2one(related='helpdesk_ticket_id.lot_id', readonly=False)
    tracking = fields.Selection(related='product_id.tracking')
    suitable_product_ids = fields.Many2many(related='helpdesk_ticket_id.suitable_product_ids', export_string_translation=False)

    def reverse_moves(self, is_modify=False):
        action = super().reverse_moves(is_modify=is_modify)
        if self.helpdesk_ticket_id:  # checking if the wizard was created from helpdesk
            if self.sudo().product_id and self.new_move_ids.invoice_line_ids.product_id != self.sudo().product_id:
                self.new_move_ids.invoice_line_ids = self.new_move_ids.invoice_line_ids.filtered(lambda line: line.product_id == self.sudo().product_id)
            for line in self.new_move_ids.invoice_line_ids:  # self.new_move_ids is the reverse of the moves passed to the wizard
                # the line could be a down payment, which has display_type == 'product'; we have to check if there is a product
                if not line.product_id or line.display_type != 'product' or line.product_id.type != 'consu' or line.product_id != self.product_id:
                    continue
                # for helpdesk, we are guaranteed to always have a single sale line
                line.quantity -= line.sale_line_ids.qty_delivered
        return action

    def _get_default_so_domain(self, ticket):
        domain = super()._get_default_so_domain(ticket)
        if product := ticket.sudo().product_id:
            domain = expression.AND([
                domain,
                [('order_line.product_id', '=', product.id)]
            ])
        return domain

    def _get_default_moves_domain(self, ticket):
        domain = super()._get_default_moves_domain(ticket)
        if ticket.product_id:
            domain = expression.AND([
                domain,
                [('line_ids.product_id', '=', ticket.product_id.id)]
            ])
        return domain

    def _get_suitable_move_domain(self):
        domain = super()._get_suitable_move_domain()
        if self.helpdesk_ticket_id.product_id:
            domain = expression.AND([
                domain,
                [('invoice_line_ids.product_id', '=', self.helpdesk_ticket_id.product_id.id)]
            ])
        return domain

    def _get_suitable_so_domain(self):
        domain = super()._get_suitable_so_domain()
        if product := self.helpdesk_ticket_id.sudo().product_id:
            domain = expression.AND([
                domain,
                [('order_line.product_id', '=', product.id)]
            ])
        return domain
