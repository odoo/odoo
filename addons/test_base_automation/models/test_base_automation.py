# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
from odoo import fields, models, api


class BaseAutomationLeadTest(models.Model):
    _name = 'base.automation.lead.test'
    _description = "Automated Rule Test"

    name = fields.Char(string='Subject', required=True)
    user_id = fields.Many2one('res.users', string='Responsible')
    state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('open', 'In Progress'),
                              ('pending', 'Pending'), ('done', 'Closed')],
                             string="Status", readonly=True, default='draft')
    active = fields.Boolean(default=True)
    tag_ids = fields.Many2many('test_base_automation.tag')
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_automation_last = fields.Datetime(string='Last Automation', readonly=True)
    employee = fields.Boolean(compute='_compute_employee_deadline', store=True)
    line_ids = fields.One2many('base.automation.line.test', 'lead_id')

    priority = fields.Boolean()
    deadline = fields.Boolean(compute='_compute_employee_deadline', store=True)
    is_assigned_to_admin = fields.Boolean(string='Assigned to admin user')

    stage_id = fields.Many2one(
        'test_base_automation.stage', string='Stage',
        compute='_compute_stage_id', readonly=False, store=True)

    @api.depends('state')
    def _compute_stage_id(self):
        Test_Base_AutomationStage = self.env['test_base_automation.stage']
        for task in self:
            if not task.stage_id and task.state == 'draft':
                task.stage_id = (
                    Test_Base_AutomationStage.search([('name', 'ilike', 'new')], limit=1)
                    or Test_Base_AutomationStage.create({'name': 'New'})
                )

    @api.depends('partner_id.employee', 'priority')
    def _compute_employee_deadline(self):
        # this method computes two fields on purpose; don't split it
        for record in self:
            record.employee = record.partner_id.employee
            if not record.priority or not record.create_date:
                record.deadline = False
            else:
                record.deadline = record.create_date + relativedelta.relativedelta(days=3)

    def write(self, vals):
        result = super().write(vals)
        # force recomputation of field 'deadline' via 'employee': the action
        # based on 'deadline' must be triggered
        self.mapped('employee')
        return result


class BaseAutomationLeadThreadTest(models.Model):
    _name = 'base.automation.lead.thread.test'
    _description = "Automated Rule Test With Thread"
    _inherit = ['base.automation.lead.test', 'mail.thread']

    user_id = fields.Many2one("res.users")

class BaseAutomationLineTest(models.Model):
    _name = 'base.automation.line.test'
    _description = "Automated Rule Line Test"

    name = fields.Char()
    lead_id = fields.Many2one('base.automation.lead.test', ondelete='cascade')
    user_id = fields.Many2one('res.users')


class BaseAutomationLinkTest(models.Model):
    _name = 'base.automation.link.test'
    _description = "Automated Rule Link Test"

    name = fields.Char()
    linked_id = fields.Many2one('base.automation.linked.test', ondelete='cascade')


class BaseAutomationLinkedTest(models.Model):
    _name = 'base.automation.linked.test'
    _description = "Automated Rule Linked Test"

    name = fields.Char()
    another_field = fields.Char()


class Test_Base_AutomationProject(models.Model):
    _name = 'test_base_automation.project'
    _description = 'test_base_automation.project'

    name = fields.Char()
    task_ids = fields.One2many('test_base_automation.task', 'project_id')
    stage_id = fields.Many2one('test_base_automation.stage')
    tag_ids = fields.Many2many('test_base_automation.tag')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], default='1')
    user_ids = fields.Many2many('res.users')


class Test_Base_AutomationTask(models.Model):
    _name = 'test_base_automation.task'
    _description = 'test_base_automation.task'

    name = fields.Char()
    parent_id = fields.Many2one('test_base_automation.task')
    project_id = fields.Many2one(
        'test_base_automation.project',
        compute='_compute_project_id', recursive=True, store=True, readonly=False,
    )

    @api.depends('parent_id.project_id')
    def _compute_project_id(self):
        for task in self:
            if not task.project_id:
                task.project_id = task.parent_id.project_id


class Test_Base_AutomationStage(models.Model):
    _name = 'test_base_automation.stage'
    _description = 'test_base_automation.stage'
    name = fields.Char()


class Test_Base_AutomationTag(models.Model):
    _name = 'test_base_automation.tag'
    _description = 'test_base_automation.tag'
    name = fields.Char()


# pylint: disable=E0102
class BaseAutomationLeadThreadTest(models.Model):  # noqa: F811
    _name = 'base.automation.lead.thread.test'
    _inherit = ["base.automation.lead.test", "mail.thread"]
    _description = "Threaded Lead Test"


class BaseAutomationModelWithRecnameChar(models.Model):
    _name = 'base.automation.model.with.recname.char'
    _description = "Model with Char as _rec_name"
    _rec_name = "description"
    description = fields.Char()
    user_id = fields.Many2one('res.users', string='Responsible')


class BaseAutomationModelWithRecnameM2o(models.Model):
    _name = 'base.automation.model.with.recname.m2o'
    _description = "Model with Many2one as _rec_name and name_create"
    _rec_name = "user_id"
    user_id = fields.Many2one("base.automation.model.with.recname.char", string='Responsible')

    @api.model
    def name_create(self, name):
        name = name.strip()
        user = self.env["base.automation.model.with.recname.char"].search([('description', '=ilike', name)], limit=1)
        if user:
            user_id = user.id
        else:
            user_id, _user_name = self.env["base.automation.model.with.recname.char"].name_create(name)

        record = self.create({'user_id': user_id})
        return record.id, record.display_name
