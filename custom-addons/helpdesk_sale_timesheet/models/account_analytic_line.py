# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.addons.sale_timesheet_enterprise.models.sale import DEFAULT_INVOICED_TIMESHEET

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    display_sol = fields.Boolean(compute="_compute_display_sol")

    @api.depends('helpdesk_ticket_id')
    def _compute_commercial_partner(self):
        timesheets_with_ticket = self.filtered('helpdesk_ticket_id')
        super(AccountAnalyticLine, self - timesheets_with_ticket)._compute_commercial_partner()
        for line in timesheets_with_ticket:
            line.commercial_partner_id = line.helpdesk_ticket_id.commercial_partner_id

    @api.depends('helpdesk_ticket_id', 'helpdesk_ticket_id.use_helpdesk_sale_timesheet')
    def _compute_display_sol(self):
        sale_project_ids = set(self.env['project.project']._search([('helpdesk_team.use_helpdesk_sale_timesheet', '=', True)]))
        for line in self:
            if line.project_id and not line.project_id.allow_billable and line.project_id.id not in sale_project_ids:
                line.display_sol = False
            else:
                line.display_sol = not line.helpdesk_ticket_id or line.helpdesk_ticket_id.use_helpdesk_sale_timesheet

    @api.depends('helpdesk_ticket_id.sale_line_id')
    def _compute_so_line(self):
        non_billed_helpdesk_timesheets = self.filtered(lambda t: not t.is_so_line_edited and t.helpdesk_ticket_id and t._is_not_billed() and not t.validated)
        for timesheet in non_billed_helpdesk_timesheets:
            timesheet.so_line = timesheet.project_id.allow_billable and timesheet.helpdesk_ticket_id.sale_line_id
        super(AccountAnalyticLine, self - non_billed_helpdesk_timesheets)._compute_so_line()

    @api.depends('timesheet_invoice_id.state')
    def _compute_partner_id(self):
        super(AccountAnalyticLine, self.filtered(lambda t: t._is_not_billed()))._compute_partner_id()

    def _get_portal_helpdesk_timesheet(self):
        param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        if param_invoiced_timesheet == 'approved':
            return self.filtered(lambda line: line.validated)
        return self

    def _check_timesheet_can_be_billed(self):
        return super(AccountAnalyticLine, self)._check_timesheet_can_be_billed() or self.so_line == self.helpdesk_ticket_id.sale_line_id

    def _timesheet_get_sale_domain(self, order_lines_ids, invoice_ids):
        domain = super(AccountAnalyticLine, self)._timesheet_get_sale_domain(order_lines_ids, invoice_ids)
        if not invoice_ids:
            return domain

        return expression.OR([domain, [
            '&',
                '&',
                    ('task_id', '=', False),
                    ('helpdesk_ticket_id', '!=', False),
                '&',
                    ('so_line', 'in', order_lines_ids.ids),
                    ('timesheet_invoice_id', '=', False),
        ]])
