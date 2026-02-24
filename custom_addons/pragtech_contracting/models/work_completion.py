# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class WorkCompletion(models.Model):
    _name = "work.completion"
    _description = 'Work Completion'

    name = fields.Char('Name')
    workorder_id = fields.Many2one('work.order', 'WorkOrder', required=True)
    workorder_line_id = fields.Many2one('work.order.line', 'WO Detail No')
    contractor_id = fields.Many2one('res.partner', domain=[('contractor', '=', True)])
    project_wbs = fields.Many2one('project.task', 'project WBS Name', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    project_id = fields.Many2one('project.project', string='Project')
    group_id = fields.Many2one('project.task', 'Group')
    labour_id = fields.Many2one('labour.master', 'Labour')
    task_id = fields.Many2one('project.task', 'Task')
    forecast_completion = fields.Date('Forecast Completion')

    estimated_qty = fields.Integer('Quantity')
    stage_id = fields.Many2one('stage.master', 'Stage')
    order_line = fields.One2many('work.completion.line', 'order_id', string=' Order lines', ondelete='cascade')
    labour_estimate_sequence = fields.Char(' ')
    total_percent = fields.Float('Total (%)', compute='get_total', store=True)
    total_quantity = fields.Float('Total Quantity', compute='get_total_quantity', store=True)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)

    amt_to_release = fields.Float(string='Amount to release', help='This is amount to release after completion of task which is specified in payment schedule.')
    payment_schedule_id = fields.Many2one('payment.schedule', 'Payment Schedule')

    def unlink(self):
        for line in self.order_line:
            if line.stage_id.approved:
                raise UserError(_('You cannot delete this record as some completions are approved.'))

        return models.Model.unlink(self)

    @api.depends('order_line.completion_percent', 'order_line.stage_id')
    def get_total(self):
        sum = 0
        for line in self.order_line:
            stage_master_obj = self.env['stage.master'].search([('approved', '=', True)], limit=1)
            if line.stage_id.id == stage_master_obj.id:
                sum = sum + line.completion_percent

        self.total_percent = sum
        return sum

    def calculate_total(self):
        return True

    @api.depends('order_line.completion_percent', 'order_line.stage_id')
    def get_total_quantity(self):
        sum = 0
        for line in self.order_line:
            stage_master_obj = self.env['stage.master'].search([('approved', '=', True)], limit=1)
            if line.stage_id == stage_master_obj:
                sum = sum + line.completion_qty

        self.total_quantity = sum
        return sum

    def write(self, vals):
        msg_ids = {}
        """ If forecast completion date will change then log record will create."""
        if vals.get('forecast_completion'):
            msg_ids = {
                'date': datetime.now(),
                'remark': 'Forecast Completion-' + vals.get('forecast_completion'),
                'author_id': self._context.get('uid'),
                'model': 'work.completion',
                'res_id': self.id,
            }
            self.mesge_ids.create(msg_ids)

        res = super(WorkCompletion, self).write(vals)
        if self.total_percent > 100 or self.total_quantity > self.estimated_qty:
            raise UserError(_('Invalid Percentage Amount.'))

        total_percent = 0
        for line in self.order_line:
            total_percent += line.completion_percent
            if (total_percent) > 100 or line.completion_qty == 0:
                raise UserError(_('Please Enter valid Percent Amount.'))

        return res


class WorkCompletionLine(models.Model):
    _name = "work.completion.line"
    _description = 'Work Completion Line'

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        for vals in vals_list:
            existing_stage = []
            st_id = self.env['stage.master'].search([('draft', '=', True)])
            msg_ids = {
                'date': datetime.now(),
                'from_stage': None,
                'to_stage': st_id.id,
                'remark': None,
                'res_id': self.id,
                'model': 'work.completion.line'
            }
            existing_stage.append((0, 0, msg_ids))
            vals.update({
                'compl_line_mesge_ids': existing_stage
            })

        return super(WorkCompletionLine, self).create(vals_list)

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    date_of_completion = fields.Datetime('Date of Completion', required=True)
    completion_qty = fields.Float(string='Completion Quantity', required=True)
    completion_percent = fields.Float(string='Completion (%)', required=True)
    executed_by = fields.Many2one('res.partner', 'Executed By', compute='get_value')
    completion_remark = fields.Text('Remark')
    order_id = fields.Many2one('work.completion', string='Work Completion Reference', ondelete='cascade')
    task_id = fields.Many2one('project.task', related='order_id.task_id', store=True)
    flag = fields.Boolean(' ')
    sequence = fields.Integer('Seq.')
    completion_no = fields.Integer('seq.')
    bill = fields.Many2one('ra.bill', string='Bill')
    compl_line_mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)
    counter = 0
    create_counter = 0

    def get_value(self):
        for this in self:
            partner = this.order_id.workorder_id.partner_id
            this.executed_by = partner
            return partner

    @api.onchange('completion_qty')
    def onchange_completion_qty(self):
        if self.order_id.estimated_qty != 0:
            self.completion_percent = (self.completion_qty / self.order_id.estimated_qty) * 100

    @api.onchange('completion_percent')
    def onchange_completion_percent(self):
        if self.order_id.estimated_qty != 0:
            self.completion_qty = (self.completion_percent * self.order_id.estimated_qty) / 100

    def unlink(self):
        for this in self:
            if this.stage_id.approved:
                raise UserError(_('You cannot delete approved completion.'))

        return models.Model.unlink(self)

    def change_state(self, context={}):
        """ Updating task completion progress (%) in task """
        if self.counter == 0:
            if context.get('copy') == True:
                self.sequence = self.env['ir.sequence'].next_by_code('work.completion.line') or '/'

                self.flag = 1
                task_obj = self.env['project.task'].browse(self.order_id.task_id.id)
                if not (self.completion_percent + task_obj.percentage) > 100:
                    task_obj.write({'percentage': (self.completion_percent + task_obj.percentage)})

                    if self.completion_percent == 100:
                        task_obj.write({
                            'actual_finish_date': datetime.now(),
                            'status': 'completed'
                        })
                """ creating sequence """

            view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }

