# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import models, fields, api
from datetime import datetime, timedelta


class WizardWorkCompletion(models.TransientModel):
    _name = "wizard.work.completion"
    _description = "Wizard Completion"

    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)], required=True)
    project_id = fields.Many2one('project.project', 'Project', required=True)
    sub_project = fields.Many2one('sub.project', 'Sub Project', required=True)
    task_category = fields.Many2many('task.category', 'task_req_task_categ_rel', 'requisition_id', 'task_category_id', string='Task Category')
    labour_category = fields.Many2many('labour.category', 'wo_completion_lbr_cat_rel', 'labour_cat_id', 'wo_compl_wizard_id', string='Labour Category')

    labour_id = fields.Many2one('labour.master', 'Labour')
    group_id = fields.Many2one('project.task', 'Group')
    task_id = fields.Many2one('project.task', 'Task')
    completion_task_line_ids = fields.One2many('wizard.work.completion.task', 'work_completion_id', string='Requisition Order')
    from_date = fields.Date('From Date', default=str(datetime.now() + timedelta(days=-30)).split(' ')[0], required=True)
    to_date = fields.Date('To Date', default=lambda self: fields.Date.context_today(self) + timedelta(days=1), required=True)
    is_use = fields.Boolean(' ')

    task_date_type = fields.Selection([('planned', 'Planned'), ('actual', 'Actual')], string='Task Date Type', default='planned')
    date_type = fields.Selection([('start_date', 'Start Date'), ('finish_date', 'Finish Date')], default='start_date', string='Date Type')

    completion = fields.Selection([('all', 'All'), ('completed', 'Completed'), ('not_completed', 'Not Completed')], default='all')

    @api.depends('sub_project')
    @api.onchange('sub_project')
    def sub_project_onchange(self):
        project_lst = []
        project_ids = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sub_project', '=', self.sub_project.id)])
        for i in project_ids:
            project_lst.append(i.name)

        return {
            'project_wbs': {
                'name': [('name', 'in', project_lst)]
            }
        }

    @api.depends('task_category')
    @api.onchange('task_category')
    def task_category_onchange(self):
        cat_list = []
        for line in self.task_category:
            cat_list.append(line.id)
        return {
            'domain': {
                'task_id': [('category_id', 'in', cat_list), ('is_task', '=', True), ('project_wbs_id', '=', self.project_wbs.id)]
            }
        }

    @api.depends('labour_category')
    @api.onchange('labour_category')
    def labour_category_onchange(self):
        cat_list = []
        for line in self.labour_category:
            cat_list.append(line.id)

        return {
            'domain': {
                'labour_id': [('category_id', '=', self.labour_category.id), ('is_labour', '=', True)]
            }
        }

    @api.depends('project_id', 'project_wbs', 'group_id', 'task_category', 'task_id', 'labour_category', 'labour_id')
    def compute_task_lines(self):
        # Search from different fields and add requisition depending on search
        # result
        self.completion_task_line_ids.unlink()
        vals = {}
        workorder_list = []
        domain = []
        wo_domain = []
        task_category_lst = []
        labour_category_lst = []
        if self.project_id:
            wo_domain.append(('project_id', '=', self.project_id.id))
        if self.project_wbs:
            wo_domain.append(('project_wbs', '=', self.project_wbs.id))
        if self.sub_project:
            wo_domain.append(('sub_project', '=', self.sub_project.id))
        if self.workorder_id:
            wo_domain.append(('id', '=', self.workorder_id.id))

        workorder_obj = self.env['work.order'].search(wo_domain)
        for order in workorder_obj:
            for line in order:
                workorder_list.append(line.id)

        domain.append(('order_id', 'in', workorder_list))
        if self.task_category:
            for i in self.task_category:
                task_category_lst.append(i.id)

            domain.append(('task_category', 'in', task_category_lst))

        if self.labour_category:
            for i in self.labour_category:
                labour_category_lst.append(i.id)

            domain.append(('category_id', 'in', labour_category_lst))

        if self.labour_id:
            domain.append(('labour_id', '=', self.labour_id.id))

        if self.task_id:
            domain.append(('task_id', '=', self.task_id.id))

        wo_line_obj = self.env['work.order.line'].search(domain)

        for wo_line in wo_line_obj:
            for line in wo_line.payment_schedule_line_ids:
                vals.update({
                    'work_completion_id': self.id,
                    'labour_id': wo_line.labour_id.id,
                    'labour_uom_qty': wo_line.quantity,
                    'labour_uom': 6,
                    'labour_rate': wo_line.rate,
                    'workorder_id': wo_line.order_id.id,
                    'workorder_line_id': wo_line.id,
                    'amt_to_release': line.amount_to_release,
                    'payment_schedule_id': line.id
                })

                if self.task_id:
                    if line.task_id == self.task_id:
                        vals.update({'task_id': self.task_id.id, })
                else:
                    vals.update({'task_id': line.task_id.id, })

                if self.completion == 'completed':
                    if line.completion_id.total_percent == 100.0:
                        self.env['wizard.work.completion.task'].create(vals)
                elif self.completion == 'not_completed':
                    if line.completion_id.total_percent < 100.0 and line.completion_id.total_percent > 0.0:
                        self.env['wizard.work.completion.task'].create(vals)
                else:
                    self.env['wizard.work.completion.task'].create(vals)

        view_id = self.env.ref('pragtech_contracting.work_requisition_wizard_form_view').id
        return {
            'name': _("Create Work Completion"),
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'wizard.work.completion',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class WizardWorkCompletionTask(models.TransientModel):
    _name = "wizard.work.completion.task"
    _description = "Wizard Work Completion Task"

    task_id = fields.Many2one('project.task', 'Task')
    remark = fields.Char('Remark')
    work_completion_id = fields.Many2one('wizard.work.completion', 'Work Requisition')
    is_use = fields.Boolean(' ')
    project_id = fields.Many2one('project.project', related='work_completion_id.project_id', store=True, string='Project')
    sub_project = fields.Many2one('sub.project', related='work_completion_id.sub_project', string='Sub Project', required=True)
    project_wbs = fields.Many2one('project.task', related='work_completion_id.project_wbs', store=True, string='Project Wbs')
    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    workorder_line_id = fields.Many2one('work.order.line', 'WO Detail No')
    labour_estimate_sequence = fields.Char(readonly=True)
    labour_id = fields.Many2one('labour.master', string='Labour')
    labour_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    labour_uom_qty = fields.Float(string='Quantity', default=1.0)
    labour_rate = fields.Float(string='Rate', default=1.0)
    amt_to_release = fields.Float(string='Amount to release', help='This is amount to release after completion of task which is specified in payment schedule.')
    group_id = fields.Many2one('project.task', related='task_id.parent_task_id', store=True, string='Group')
    payment_schedule_id = fields.Many2one('payment.schedule', 'Payment Schedule')

    def get_estimated_qty(self, task_id):
        task_estimation = self.env['task.labour.line'].search([('labour_line_id', '=', task_id)], limit=1)
        return task_estimation.labour_uom_qty

    def complete_task(self):
        work_coml_obj = self.env['work.completion']
        res = self.env['work.completion']
        work_coml_obj = self.env['work.completion'].search(
            [('project_id', '=', self.project_id.id), ('sub_project', '=', self.sub_project.id), ('project_wbs', '=', self.project_wbs.id),
             ('task_id', '=', self.task_id.id), ('labour_id', '=', self.labour_id.id), ('workorder_line_id', '=', self.workorder_line_id.id), ('workorder_id', '=', self.workorder_id.id)])

        if not work_coml_obj:
            qty = self.get_estimated_qty(self.task_id.id)
            vals = {
                'name': self.env['ir.sequence'].next_by_code('work.completion') or '/',
                'project_id': self.work_completion_id.project_id.id,
                'project_wbs': self.work_completion_id.project_wbs.id,
                'sub_project': self.work_completion_id.sub_project.id,
                'group_id': self.group_id.id,
                'labour_id': self.labour_id.id,
                'task_id': self.task_id.id,
                'forecast_completion': self.task_id.planned_finish_date,
                'estimated_qty': self.labour_uom_qty,
                'labour_estimate_sequence': self.labour_estimate_sequence,
                'workorder_id': self.workorder_id.id,
                'workorder_line_id': self.workorder_line_id.id,
                'contractor_id': self.workorder_id.partner_id.id,
                'amt_to_release': self.amt_to_release,
                'payment_schedule_id': self.payment_schedule_id.id
            }

            res = self.env['work.completion'].create(vals)
            msg_ids = {
                'date': datetime.now(),
                'author_id': self._context.get('uid'),
                'model': 'work.completion', 'res_id': res.id
            }
            self.env['mail.messages'].create(msg_ids)

        if res:
            """ Setting Completion id in payment schedule table """
            self.payment_schedule_id.completion_id = res.id
            view_id = self.env.ref('pragtech_contracting.work_completion_form').id
            return {
                'name': _("Task Completion Progress"),
                'context': self.env.context,
                'view_mode': 'form',
                'views': [(view_id, 'form')],
                'res_model': 'work.completion',
                'res_id': res.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
            }

        if work_coml_obj and not res:
            view_id = self.env.ref('pragtech_contracting.work_completion_form').id
            return {
                'name': _("Task Completion Progress"),
                'context': self.env.context,
                'view_mode': 'form',
                'views': [(view_id, 'form')],
                'res_model': 'work.completion',
                'res_id': work_coml_obj.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
            }

