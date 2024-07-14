# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    repairs_count = fields.Integer('Repairs Count', compute='_compute_repairs_count', compute_sudo=True)
    repair_ids = fields.One2many('repair.order', 'ticket_id', string='Repairs', copy=False)

    @api.depends('repair_ids')
    def _compute_repairs_count(self):
        repair_data = self.env['repair.order'].sudo()._read_group([('ticket_id', 'in', self.ids)], ['ticket_id'], ['__count'])
        mapped_data = {ticket.id: count for ticket, count in repair_data}
        for ticket in self:
            ticket.repairs_count = mapped_data.get(ticket.id, 0)

    def action_view_repairs(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Repairs'),
            'res_model': 'repair.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.repair_ids.ids)],
        }
        action['context'] = self._prepare_repairs_default_value()
        if self.repairs_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.repair_ids.id
            })
        return action

    def action_repair_order_form(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id("helpdesk_repair.action_repair_order_form")
        action['context'] = self._prepare_repairs_default_value()
        return action

    def _prepare_repairs_default_value(self):
        return {
            **self.env.context,
            'default_product_id': self.product_id.id,
            'default_lot_id': self.lot_id.id,
            'default_partner_id': self.partner_id.id,
            'default_ticket_id': self.id,
            'default_company_id': self.company_id.id,
            'default_description': self.name,
            'default_sale_order_id': self.sale_order_id.id,
            'default_user_id': False,
            'default_internal_notes': self.description,
            'default_picking_id': self.picking_ids.filtered(lambda x: x.product_id == self.product_id)[-1].id
                if self.picking_ids and self.product_id else self.picking_ids[-1:].id,
        }
