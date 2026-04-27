# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.misc import unquote


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def _domain_sale_line_id(self):
        domain = expression.AND([
            self.env['sale.order.line']._sellable_lines_domain(),
            self.env['sale.order.line']._domain_sale_line_service(),
            [
                ('company_id', '=', unquote('company_id')),
                ('order_partner_id', 'child_of', unquote('commercial_partner_id')),
            ],
        ])
        return domain

    use_helpdesk_sale_timesheet = fields.Boolean('Reinvoicing Timesheet activated on Team', related='team_id.use_helpdesk_sale_timesheet', readonly=True)
    sale_order_id = fields.Many2one('sale.order', compute="_compute_helpdesk_sale_order", compute_sudo=True, store=True, readonly=False)
    invoice_count = fields.Integer(related='sale_order_id.invoice_count', export_string_translation=False)
    display_invoice_button = fields.Boolean(compute='_compute_display_invoice_button', compute_sudo=True, export_string_translation=False)
    sale_line_id = fields.Many2one(
        'sale.order.line', string="Sales Order Item", tracking=True,
        compute="_compute_sale_line_id", store=True, readonly=False,
        domain=lambda self: str(self._domain_sale_line_id()),
        help="Sales Order Item to which the time spent on this ticket will be added in order to be invoiced to your customer.\n"
             "By default the last prepaid sales order item that has time remaining will be selected.\n"
             "Remove the sales order item in order to make this ticket non-billable.\n"
             "You can also change or remove the sales order item of each timesheet entry individually.")
    remaining_hours_available = fields.Boolean(related="sale_line_id.remaining_hours_available", export_string_translation=False)
    remaining_hours_so = fields.Float('Time Remaining on SO', compute='_compute_remaining_hours_so', search='_search_remaining_hours_so', aggregator="avg")

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for ticket in self:
            if ticket.sale_line_id and not ticket.sale_line_id.is_service:
                raise ValidationError(_(
                    'You cannot link order item %(order_id)s - %(product_id)s to this ticket because it is not a service product.',
                    order_id=ticket.sale_line_id.order_id.name,
                    product_id=ticket.sale_line_id.product_id.display_name,
                ))

    @api.depends('sale_line_id', 'timesheet_ids', 'timesheet_ids.unit_amount')
    def _compute_remaining_hours_so(self):
        # TODO This is not yet perfectly working as timesheet.so_line stick to its old value although changed
        #      in the task From View.
        timesheets = self.timesheet_ids.filtered(lambda t: t.helpdesk_ticket_id.sale_line_id in (t.so_line, t._origin.so_line) and t.so_line.remaining_hours_available)

        mapped_remaining_hours = {ticket._origin.id: ticket.sale_line_id and ticket.sale_line_id.remaining_hours or 0.0 for ticket in self}
        uom_hour = self.env.ref('uom.product_uom_hour')
        for timesheet in timesheets:
            delta = 0
            if timesheet._origin.so_line == timesheet.helpdesk_ticket_id.sale_line_id:
                delta += timesheet._origin.unit_amount
            if timesheet.so_line == timesheet.helpdesk_ticket_id.sale_line_id:
                delta -= timesheet.unit_amount
            if delta:
                mapped_remaining_hours[timesheet.helpdesk_ticket_id._origin.id] += timesheet.product_uom_id._compute_quantity(delta, uom_hour)

        for ticket in self:
            ticket.remaining_hours_so = mapped_remaining_hours[ticket._origin.id]

    @api.model
    def _search_remaining_hours_so(self, operator, value):
        return [('sale_line_id.remaining_hours', operator, value)]

    @api.depends('partner_id', 'use_helpdesk_sale_timesheet', 'project_id.pricing_type', 'project_id.sale_line_id')
    def _compute_sale_line_id(self):
        billable_tickets = self.filtered('use_helpdesk_sale_timesheet')
        (self - billable_tickets).update({
            'sale_line_id': False
        })
        for ticket in billable_tickets:
            if ticket.project_id and ticket.project_id.pricing_type != 'task_rate':
                ticket.sale_line_id = ticket.project_id.sale_line_id
            # Check sale_line_id and customer are coherent
            if ticket.sale_line_id.sudo().order_partner_id.commercial_partner_id != ticket.commercial_partner_id:
                ticket.sale_line_id = False
            if not ticket.sale_line_id:
                ticket.sale_line_id = ticket._get_last_sol_of_customer()

    def _compute_display_invoice_button(self):
        for ticket in self:
            ticket.display_invoice_button = ticket.use_helpdesk_sale_timesheet and\
                (ticket.sale_order_id or ticket.sale_line_id) and ticket.invoice_count > 0

    def _get_last_sol_of_customer(self):
        # Get the last SOL made for the customer in the current task where we need to compute
        self.ensure_one()
        if not self.commercial_partner_id or not self.project_id.allow_billable or not self.use_helpdesk_sale_timesheet:
            return False
        SaleOrderLine = self.env['sale.order.line']
        domain = expression.AND([
            SaleOrderLine._domain_sale_line_service(check_state=False),
            [
                ('company_id', '=', self.company_id.id),
                ('order_partner_id', 'child_of', self.commercial_partner_id.id),
                ('state', 'in', ['sale', 'done']),
                ('remaining_hours', '>', 0),
            ],
        ])
        if self.project_id.pricing_type != 'task_rate' and (order_id := self.project_id.sale_order_id) and self.commercial_partner_id == self.project_id.partner_id.commercial_partner_id:
            domain = expression.AND([domain, [('order_id', '=?', order_id.id)]])
        return SaleOrderLine.search(domain, limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        sol_ids = {
            vals['sale_line_id']
            for vals in vals_list
            if vals.get('sale_line_id')
        }
        if sol_ids:
            tickets._ensure_sale_order_linked(list(sol_ids))
        return tickets

    def _ensure_sale_order_linked(self, sol_ids):
        quotations = self.env['sale.order.line'].sudo()._read_group(
            domain=[('state', '=', 'draft'), ('id', 'in', sol_ids)],
            aggregates=['order_id:recordset'],
        )[0][0]
        if quotations:
            quotations.action_confirm()

    def write(self, values):
        recompute_so_lines = None
        other_timesheets = None
        if 'timesheet_ids' in values and isinstance(values.get('timesheet_ids'), (tuple, list)):
            # Then, we check if the list contains tuples/lists like "(code=1, timesheet_id, vals)" and we extract timesheet_id if it is an update and 'so_line' in vals
            timesheet_ids = [command[1] for command in values.get('timesheet_ids') if isinstance(command, (list, tuple)) and command[0] == 1 and 'so_line' in command[2]]
            recompute_so_lines = self.timesheet_ids.filtered(lambda t: t.id in timesheet_ids).mapped('so_line')
            if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver') and values.get('sale_line_id', None):
                # We need to search the timesheets of other employee to update the so_line
                other_timesheets = self.env['account.analytic.line'].sudo().search([('id', 'not in', timesheet_ids), ('helpdesk_ticket_id', '=', self.id)])

        res = super(HelpdeskTicket, self).write(values)
        if sol_id := values.get('sale_line_id'):
            self._ensure_sale_order_linked([sol_id])
        if other_timesheets:
            # Then we update the so_line if needed
            compute_timesheets = defaultdict(list, [(timesheet, timesheet.so_line) for timesheet in other_timesheets])  # key = timesheet and value = so_line of the timesheet before the _compute_so_line
            other_timesheets._compute_so_line()
            for timesheet, sol in compute_timesheets.items():
                if timesheet.so_line != sol:
                    recompute_so_lines |= sol
        if recompute_so_lines:
            recompute_so_lines._compute_qty_delivered()
        return res

    @api.depends('sale_line_id', 'project_id.sale_order_id')
    def _compute_helpdesk_sale_order(self):
        for ticket in self:
            if ticket.sale_line_id:
                ticket.sale_order_id = ticket.sale_line_id.order_id
            elif ticket.project_id.sale_order_id:
                ticket.sale_order_id = ticket.project_id.sale_order_id
            else:
                ticket.sale_order_id = False
            if ticket.sale_order_id and not ticket.partner_id:
                ticket.partner_id = ticket.sale_order_id.partner_id

    @api.model
    def _sla_reset_trigger(self):
        field_list = super()._sla_reset_trigger()
        field_list.append('sale_line_id')
        return field_list

    def _sla_find_false_domain(self):
        return expression.AND([
            super()._sla_find_false_domain(),
            [('product_ids', '=', False)],
        ])

    def _sla_find_extra_domain(self):
        self.ensure_one()
        return expression.OR([
            super()._sla_find_extra_domain(),
            [('product_ids', 'in', self.sale_line_id.product_template_id.ids)],
        ])

    def action_view_so(self):
        self.ensure_one()
        action_window = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "name": _("Sales Order"),
            "views": [[False, "form"]],
            "context": {"create": False, "show_sale": True},
            "res_id": self.sale_line_id.order_id.id or self.sale_order_id.id
        }
        return action_window

    def action_view_invoices(self):
        self.ensure_one()
        invoices = self.sale_order_id.invoice_ids
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "name": _("Invoices"),
            "views": [[False, 'form']] if len(invoices) == 1 else [[False, "list"], [False, "form"]],
            "context": {"create": False},
            "domain": [('id', 'in', invoices.ids)],
            "res_id": invoices.id if len(invoices) == 1 else False,
        }
