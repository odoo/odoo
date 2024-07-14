# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ticket_count = fields.Integer(string='Ticket Count', compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        if not self.env.user.has_group('helpdesk.group_helpdesk_user'):
            self.ticket_count = 0
            return

        ticket_data = self.env['helpdesk.ticket']._read_group([
            '|', ('sale_order_id', 'in', self.ids),
            ('sale_line_id', 'in', self.order_line.ids),
            ('use_helpdesk_sale_timesheet', '=', True)
        ], ['sale_order_id'], ['__count'])
        mapped_data = {sale_order.id: count for sale_order, count in ticket_data}
        for so in self:
            so.ticket_count = mapped_data.get(so.id, 0)

    def _action_confirm(self):
        res = super()._action_confirm()
        for sla in self.order_line.product_template_id.sla_id:
            order_lines = self.order_line.filtered(lambda x: x.product_template_id.sla_id == sla)
            sla.write({
                'sale_line_ids': [Command.link(l.id) for l in order_lines],
            })
        return res

    def action_view_tickets(self):
        self.ensure_one()
        sorted_line = self.order_line.sorted('sequence')
        default_sale_line = next((sol for sol in sorted_line if sol.product_id.detailed_type == 'service'), self.env['sale.order.line'])
        if self.ticket_count > 1:
            action = self.env["ir.actions.actions"]._for_xml_id('helpdesk.helpdesk_ticket_action_main_tree')
            action.update({
                'domain': ['|', ('sale_order_id', '=', self.id), ('sale_line_id', 'in', self.order_line.ids)],
                'context': self._get_ticket_action_context(default_sale_line),
            })
            return action
        else:
            ticket = self.env['helpdesk.ticket']._search(['|', ('sale_order_id', '=', self.id), ('sale_line_id', 'in', self.order_line.ids)], limit=1)
            return {
                'type': 'ir.actions.act_window',
                'name': _('Ticket'),
                'res_model': 'helpdesk.ticket',
                'views': [(self.env.ref('helpdesk_sale_timesheet.helpdesk_ticket_view_form_inherit_helpdesk_sale_timesheet').id, 'form')],
                'res_id': list(ticket)[0],
                'context': self._get_ticket_action_context(default_sale_line),
            }

    def _get_ticket_action_context(self, default_line):
        helpdesk_team = self.env['helpdesk.team'].search([('use_helpdesk_sale_timesheet', '=', True)], order='sequence', limit=1)
        return {
            **self.env.context,
            'default_sale_line_id': default_line.id,
            'default_partner_id': self.partner_id.id,
            'default_sale_order_id': self.id,
            'default_team_id': helpdesk_team.id,
            'default_company_id': self.company_id.id,
        }
