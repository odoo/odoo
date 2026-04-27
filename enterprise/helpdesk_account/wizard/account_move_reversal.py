# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import Command, models, fields, api, _


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.model
    def _get_default_so_domain(self, ticket):
        return [('partner_id', '=', ticket.partner_id.id), ('state', '=', 'sale'), ('invoice_ids.state', '=', 'posted'), ('invoice_ids.move_type', '=', 'out_invoice')]

    @api.model
    def _get_default_moves_domain(self, ticket):
        return [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('reversal_move_ids', '=', False)]

    @api.model
    def default_get(self, fields):
        result = super(AccountMoveReversal, self).default_get(fields)
        ticket_id = result.get('helpdesk_ticket_id')
        if ticket_id:
            if 'reason' in fields:
                result['reason'] = _('Helpdesk Ticket #%s', ticket_id)
            # set default Invoice
            ticket = self.env['helpdesk.ticket'].browse(ticket_id)
            domain = self._get_default_so_domain(ticket)
            last_so = self.env['sale.order'].search(domain, limit=1, order='date_order desc')
            if last_so:
                result['helpdesk_sale_order_id'] = last_so.id
                moves = last_so.invoice_ids.filtered_domain(self._get_default_moves_domain(ticket))
                if moves:
                    result['move_ids'] = [Command.set(moves.ids)]
        return result

    # Add compute method
    move_ids = fields.Many2many('account.move', 'account_move_reversal_move', 'reversal_id', 'move_id',
        compute="_compute_move_ids", readonly=False, store=True, required=True)
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', export_string_translation=False)
    helpdesk_sale_order_id = fields.Many2one('sale.order', string='Sales Order', domain="[('id', 'in', suitable_sale_order_ids)]")
    suitable_move_ids = fields.Many2many('account.move', compute='_compute_suitable_moves', export_string_translation=False)
    suitable_sale_order_ids = fields.Many2many('sale.order', compute='_compute_suitable_sale_orders', export_string_translation=False)

    @api.depends('helpdesk_sale_order_id')
    def _compute_move_ids(self):
        for r in self.filtered('helpdesk_sale_order_id'):
            r.move_ids = r.helpdesk_sale_order_id.invoice_ids.filtered(lambda move: move.state == 'posted' and move.move_type == 'out_invoice' and not move.reversal_move_ids)

    def _get_suitable_move_domain(self):
        self.ensure_one()
        domain = [('state', '=', 'posted'), ('move_type', '=', 'out_invoice')]
        if self.helpdesk_ticket_id.partner_id:
            domain.append(('partner_id', 'child_of', self.helpdesk_ticket_id.partner_id.commercial_partner_id.id))
        if self.helpdesk_sale_order_id:
            domain.append(('id', 'in', self.helpdesk_sale_order_id.invoice_ids.ids))
        if all(reversal_move.payment_state in ['paid', 'in_payment'] for reversal_move in self.helpdesk_sale_order_id.invoice_ids.reversal_move_ids):
            domain.append(('reversal_move_ids', '=', False))
        return domain

    @api.depends('helpdesk_ticket_id.sale_order_id.invoice_ids', 'helpdesk_ticket_id.partner_id.commercial_partner_id', 'helpdesk_sale_order_id')
    def _compute_suitable_moves(self):
        for r in self:
            domain = r._get_suitable_move_domain()
            r.suitable_move_ids = self.env['account.move'].search(domain)

    def _get_suitable_so_domain(self):
        self.ensure_one()
        domain = [('state', '=', 'sale'), ('invoice_ids.state', '=', 'posted'), ('invoice_ids.move_type', '=', 'out_invoice')]
        if self.helpdesk_ticket_id.partner_id:
            domain += [('partner_id', 'child_of', self.helpdesk_ticket_id.partner_id.commercial_partner_id.id)]
        return domain

    @api.depends('helpdesk_ticket_id.partner_id.commercial_partner_id')
    def _compute_suitable_sale_orders(self):
        for r in self:
            domain = r._get_suitable_so_domain()
            r.suitable_sale_order_ids = self.env['sale.order'].search(domain)

    def reverse_moves(self, is_modify=False):
        # OVERRIDE
        res = super(AccountMoveReversal, self).reverse_moves(is_modify)

        if self.helpdesk_ticket_id:
            self.helpdesk_ticket_id.invoice_ids |= self.new_move_ids
            message = _('Refund created')
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('helpdesk_account.mt_ticket_refund_created')
            for move_id in self.new_move_ids:
                move_id.message_post_with_source(
                    'helpdesk.ticket_creation',
                    render_values={'self': move_id, 'ticket': self.helpdesk_ticket_id},
                    subtype_id=subtype_id,
                )
                self.helpdesk_ticket_id.message_post_with_source(
                    'helpdesk.ticket_conversion_link',
                    render_values={'created_record': move_id, 'message': message},
                    subtype_id=subtype_id,
                )

        return res
