# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Timesheet(models.Model):
    _inherit = 'account.analytic.line'

    task_id = fields.Many2one('project.task', 'Task', index=True)
    project_id = fields.Many2one('project.project', 'Project', domain=[('allow_timesheets', '=', True)])

    @api.onchange('project_id')
    def onchange_project_id(self):
        # force domain on task when project is set
        if self.is_timesheet and self.project_id:
            if self.project_id != self.task_id.project_id:
                # reset task when changing project
                self.task_id = False
            return {'domain': {
                'task_id': [('project_id', '=', self.project_id.id)]
            }}

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if self.is_timesheet and not self.project_id:
            self.project_id = self.task_id.project_id

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    @api.model
    def _is_timesheet(self, values):
        result = super(Timesheet, self)._is_timesheet(values)
        if not result and self._context.get('default_project_id'):  # retro compatibility for the UI
            _logger.warning("Determine timesheet use case with project_id set: this should be deprecated baby !")
            return True
        return result

    def _timesheet_preprocess(self, vals):
        # project implies analytic account
        if vals.get('project_id') and not vals.get('account_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['account_id'] = project.analytic_account_id.id
            vals['company_id'] = project.analytic_account_id.company_id.id
            if not project.analytic_account_id.active:
                raise UserError(_('The project you are timesheeting on is not linked to an active analytic account. Set one on the project configuration.'))

        vals = super(Timesheet, self)._timesheet_preprocess(vals)

        # force customer partner, from the task or the project
        if (vals.get('project_id') or vals.get('task_id')) and not vals.get('partner_id'):
            partner_id = False
            if vals.get('task_id'):
                partner_id = self.env['project.task'].browse(vals['task_id']).partner_id.id
            else:
                partner_id = self.env['project.project'].browse(vals['project_id']).partner_id.id
            if partner_id:
                vals['partner_id'] = partner_id
        return vals
