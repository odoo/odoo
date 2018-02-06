# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Line', domain=[('is_expense', '=', False)], readonly=True, help="Sale order line from which the project has been created. Used for tracability.")

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        if self.allow_timesheets:
            return self.action_view_timesheet_plan()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets of %s') % self.name,
            'domain': [('project_id', '!=', False)],
            'res_model': 'account.analytic.line',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    Record timesheets
                </p><p>
                    You can register and track your workings hours by project every
                    day. Every time spent on a project will become a cost and can be re-invoiced to
                    customers if required.
                </p>
            """),
            'limit': 80,
            'context': {
                'default_project_id': self.id,
                'search_default_project_id': [self.id]
            }
        }

    @api.multi
    def action_view_timesheet_plan(self):
        return {
            'name': _('Overview'),
            'type': 'ir.actions.client',
            'tag': 'timesheet.plan',
            'context': {
                'active_id': self.id,
                'active_ids': self.ids,
                'search_default_project_id': self.id,
            }
        }


class ProjectTask(models.Model):
    _inherit = "project.task"

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', domain="[('is_service', '=', True), ('order_partner_id', '=', partner_id), ('is_expense', '=', False)]")

    @api.multi
    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for task in self:
            if task.sale_line_id:
                if not task.sale_line_id.is_service or task.sale_line_id.is_expense:
                    raise ValidationError(_("The Sales order line should be one selling a service, and no coming from expense."))

    @api.model
    def create(self, values):
        # sub task has the same so line than their parent
        if 'parent_id' in values:
            values['sale_line_id'] = self.env['project.task'].browse(values['parent_id']).sudo().sale_line_id.id
        return super(ProjectTask, self).create(values)

    @api.multi
    def write(self, values):
        # sub task has the same so line than their parent
        if 'parent_id' in values:
            values['sale_line_id'] = self.env['project.task'].browse(values['parent_id']).sudo().sale_line_id.id

        result = super(ProjectTask, self).write(values)
        # reassign SO line on related timesheet lines
        if 'sale_line_id' in values:
            self.sudo().mapped('timesheet_ids').write({
                'so_line': values['sale_line_id']
            })
        return result

    @api.multi
    def unlink(self):
        if any(task.sale_line_id for task in self):
            raise ValidationError(_('You cannot delete a task related to a Sales Order. You can only archive this task.'))
        return super(ProjectTask, self).unlink()

    @api.multi
    def _subtask_implied_fields(self):
        fields_list = super(ProjectTask, self)._subtask_implied_fields()
        fields_list += ['sale_line_id']
        return fields_list

    @api.multi
    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    def rating_get_partner_id(self):
        partner = self.partner_id or self.sale_line_id.order_id.partner_id
        if partner:
            return partner
        return super(ProjectTask, self).rating_get_partner_id()
