# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _inherit = ['helpdesk.ticket', 'timer.mixin']

    def _default_team_id(self):
        if project_id := self.env.context.get('default_project_id'):
            if team_id := self.env['helpdesk.team'].search([('project_id', '=', project_id)], limit=1).id:
                return team_id

        return super()._default_team_id()

    team_id = fields.Many2one(domain="[('use_helpdesk_timesheet', '=', True)] if context.get('default_project_id') else []")
    project_id = fields.Many2one(
        "project.project", related="team_id.project_id", readonly=True, store=True)
    timesheet_ids = fields.One2many('account.analytic.line', 'helpdesk_ticket_id', 'Timesheets',
        help="Time spent on this ticket. By default, your timesheets will be linked to the sales order item of your ticket.\n"
             "Remove the sales order item to make your timesheet entries non billable.")
    use_helpdesk_timesheet = fields.Boolean('Timesheet activated on Team', related='team_id.use_helpdesk_timesheet', readonly=True)
    display_timesheet_timer = fields.Boolean("Display Timesheet Time", compute='_compute_display_timesheet_timer')
    total_hours_spent = fields.Float("Time Spent", compute='_compute_total_hours_spent', default=0, compute_sudo=True, store=True, aggregator="avg")
    display_timer_start_secondary = fields.Boolean(compute='_compute_display_timer_buttons', export_string_translation=False)
    display_timer = fields.Boolean(compute='_compute_display_timer', export_string_translation=False)
    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days', export_string_translation=False)
    analytic_account_id = fields.Many2one('account.analytic.account',
        compute='_compute_analytic_account_id', store=True, readonly=False,
        string='Analytic Account', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day')

    @api.depends('display_timesheet_timer', 'timer_start', 'timer_pause', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        for ticket in self:
            if not ticket.display_timesheet_timer:
                ticket.update({
                    'display_timer_start_primary': False,
                    'display_timer_start_secondary': False,
                    'display_timer_stop': False,
                    'display_timer_pause': False,
                    'display_timer_resume': False,
                })
            else:
                super(HelpdeskTicket, ticket)._compute_display_timer_buttons()
                ticket.display_timer_start_secondary = ticket.display_timer_start_primary
                if not ticket.timer_start:
                    ticket.update({
                        'display_timer_stop': False,
                        'display_timer_pause': False,
                        'display_timer_resume': False,
                    })
                    if not ticket.total_hours_spent:
                        ticket.display_timer_start_secondary = False
                    else:
                        ticket.display_timer_start_primary = False

    def _compute_display_timer(self):
        if self.env.user.has_group('helpdesk.group_helpdesk_user') and self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            self.display_timer = True
        else:
            self.display_timer = False

    @api.depends('use_helpdesk_timesheet', 'timesheet_ids', 'encode_uom_in_days')
    def _compute_display_timesheet_timer(self):
        for ticket in self:
            ticket.display_timesheet_timer = ticket.use_helpdesk_timesheet and not ticket.encode_uom_in_days

    @api.depends('timesheet_ids.unit_amount')
    def _compute_total_hours_spent(self):
        if not any(self._ids):
            for ticket in self:
                ticket.total_hours_spent = sum(ticket.timesheet_ids.mapped('unit_amount'))
            return
        timesheet_read_group = self.env['account.analytic.line']._read_group(
            [('helpdesk_ticket_id', 'in', self.ids)],
            ['helpdesk_ticket_id'],
            ['unit_amount:sum'],
        )
        timesheets_per_ticket = {helpdesk_ticket.id: unit_amount_sum for helpdesk_ticket, unit_amount_sum in timesheet_read_group}
        for ticket in self:
            ticket.total_hours_spent = timesheets_per_ticket.get(ticket.id, 0.0)

    @api.onchange('team_id')
    def _onchange_team_id(self):
        # If the new helpdesk team has no timesheet feature AND ticket has non-validated timesheets, show a warning message
        if (
            self.timesheet_ids and
            not self.team_id.use_helpdesk_timesheet and
            not all(t.validated for t in self.timesheet_ids)
        ):
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _("Moving this task to a helpdesk team without timesheet support will retain timesheet drafts in the original helpdesk team. "
                                 "Although they won't be visible here, you can still edit them using the Timesheets app."),
                    'type': "notification",
                },
            }

    @api.model_create_multi
    def create(self, list_value):
        default_project_id = self._context.get('default_project_id')
        for vals in list_value:
            project_id = vals.get('project_id') or default_project_id
            if not vals.get('team_id') and project_id:
                project = self.env['project.project'].browse(project_id)
                if project.helpdesk_team:
                    vals['team_id'] = project.helpdesk_team[0].id
        tickets = super().create(list_value)
        return tickets

    @api.depends('project_id')
    def _compute_analytic_account_id(self):
        for ticket in self:
            ticket.analytic_account_id = ticket.project_id.account_id

    @api.depends('use_helpdesk_timesheet')
    def _compute_display_extra_info(self):
        if self.env.user.has_group('analytic.group_analytic_accounting'):
            show_analytic_account_id_records = self.filtered('use_helpdesk_timesheet')
            show_analytic_account_id_records.display_extra_info = True
            super(HelpdeskTicket, self - show_analytic_account_id_records)._compute_display_extra_info()
        else:
            super()._compute_display_extra_info()

    def action_timer_start(self):
        if not self.user_timer_id.timer_start and self.display_timesheet_timer:
            super().action_timer_start()

    def action_timer_stop(self):
        # timer was either running or paused
        if self.user_timer_id.timer_start and self.display_timesheet_timer:
            minutes_spent = self.user_timer_id._get_minutes_spent()
            minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
            rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
            minutes_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding)
            return self._action_open_new_timesheet(minutes_spent * 60 / 3600)
        return False

    def _action_open_new_timesheet(self, time_spent):
        return {
            "name": _("Confirm Time Spent"),
            "type": 'ir.actions.act_window',
            "res_model": 'helpdesk.ticket.create.timesheet',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                **self.env.context,
                'active_id': self.id,
                'active_model': self._name,
                'default_time_spent': time_spent,
                'dialog_size': 'medium',
            },
        }
