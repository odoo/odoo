# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _inherit = ['helpdesk.ticket', 'timer.mixin']

    project_id = fields.Many2one(
        "project.project", related="team_id.project_id", readonly=True, store=True)
    timesheet_ids = fields.One2many('account.analytic.line', 'helpdesk_ticket_id', 'Timesheets',
        help="Time spent on this ticket. By default, your timesheets will be linked to the sales order item of your ticket.\n"
             "Remove the sales order item to make your timesheet entries non billable.")
    use_helpdesk_timesheet = fields.Boolean('Timesheet activated on Team', related='team_id.use_helpdesk_timesheet', readonly=True)
    display_timesheet_timer = fields.Boolean("Display Timesheet Time", compute='_compute_display_timesheet_timer')
    total_hours_spent = fields.Float("Hours Spent", compute='_compute_total_hours_spent', default=0, compute_sudo=True, store=True)
    display_timer_start_secondary = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer = fields.Boolean(compute='_compute_display_timer')
    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days')
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
                ticket.total_hours_spent = round(sum(ticket.timesheet_ids.mapped('unit_amount')), 2)
            return
        timesheet_read_group = self.env['account.analytic.line']._read_group(
            [('helpdesk_ticket_id', 'in', self.ids)],
            ['helpdesk_ticket_id'],
            ['unit_amount:sum'],
        )
        timesheets_per_ticket = {helpdesk_ticket.id: unit_amount_sum for helpdesk_ticket, unit_amount_sum in timesheet_read_group}
        for ticket in self:
            ticket.total_hours_spent = round(timesheets_per_ticket.get(ticket.id, 0.0), 2)

    @api.depends('project_id')
    def _compute_analytic_account_id(self):
        for ticket in self:
            ticket.analytic_account_id = ticket.project_id.analytic_account_id

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the time field labels according to the company timesheet encoding UOM
        makes the view cache dependent on the company timesheet encoding uom"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.company.timesheet_encode_uom_id,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        arch, view = super()._get_view(view_id, view_type, **options)
        arch = self.env['account.analytic.line']._apply_timesheet_label(arch)
        if view_type in ['tree', 'pivot', 'graph', 'cohort'] and self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day'):
            arch = self.env['account.analytic.line']._apply_time_label(arch, related_model=self._name)
        return arch, view

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
