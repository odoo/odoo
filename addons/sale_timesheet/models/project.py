# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Line', readonly=True, help="Sale order line from which the project has been created. Used for tracability.")

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
                <p class="oe_view_nocontent_create">
                    Click to record timesheets.
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

    @api.model
    def _default_sale_line_id(self):
        sale_line_id = False
        if self._context.get('default_parent_id'):
            sale_line_id = self.env['project.task'].browse(self._context['default_parent_id']).sale_line_id.id
        if not sale_line_id and self._context.get('default_project_id'):
            sale_line_id = self.env['project.project'].browse(self._context['default_project_id']).sale_line_id.id
        return sale_line_id

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', default=_default_sale_line_id, domain="[('is_service', '=', True), ('order_partner_id', '=', partner_id)]")

    @api.model
    def create(self, values):
        # sub task has the same so line than their parent
        parent_id = values['parent_id'] if 'parent_id' in values else self.env.context.get('default_parent_id')
        if parent_id:
            values['sale_line_id'] = self.env['project.task'].browse(parent_id).sudo().sale_line_id.id
        return super(ProjectTask, self).create(values)

    @api.multi
    def write(self, values):
        # sub task has the same so line than their parent
        if 'parent_id' in values:
            values['sale_line_id'] = self.env['project.task'].browse(values['parent_id']).sudo().sale_line_id.id

        result = super(ProjectTask, self).write(values)
        # reassign SO line on related timesheet lines
        if 'sale_line_id' in values:
            # subtasks should have the same SO line than their mother
            self.sudo().mapped('child_ids').write({
                'so_line': values['sale_line_id']
            })
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
    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        self.sale_line_id = self.parent_id.sale_line_id.id
