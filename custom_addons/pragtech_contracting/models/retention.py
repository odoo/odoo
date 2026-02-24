# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class RetentionRelease(models.Model):
    _name = 'retention.release'
    _description = 'Retention'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    def change_state(self, context={}):
        if context.get('copy') == True:
            self.state = 'paid'
            self.name = self.env['ir.sequence'].next_by_code('retention.release')
            self.flag = True
        else:
            self.flag = False

        view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
        return {
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'res_model': 'approval.wizard',
            'multi': 'True',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    project_id = fields.Many2one('project.project', string='Project')
    project_wbs = fields.Many2one('project.task', 'project WBS Name', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    contractor_id = fields.Many2one('res.partner', 'Contractor')
    workorder_id = fields.Many2one('work.order', string='Work Order')
    company_id = fields.Many2one('res.company', string='Company ID', required=True)
    release_line_ids = fields.One2many('release.line', 'retention_id')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])
    state = fields.Selection([('draft', 'Draft'), ('paid', 'Paid')], default='draft')
    name = fields.Char('Name')
    flag = fields.Boolean(' ')

    @api.depends('project_id', 'project_wbs', 'sub_project', 'contractor_id', 'workorder_id')
    @api.onchange('contractor_id')
    def onchange_contractor_id(self):
        wo_list = []
        wo_obj = self.env['work.order'].search([('partner_id', '=', self.contractor_id.id)])
        for wo in wo_obj:
            wo_list.append(wo.id)

        return {
            'domain': {
                'workorder_id': [('partner_id', '=', self.contractor_id.id)]
            }
        }

    @api.depends('project_id', 'project_wbs', 'sub_project', 'contractor_id', 'workorder_id')
    def compute_retentions(self):
        st_id = self.env['stage.master'].search([('approved', '=', True)])
        old_lines = [line.workorder_id.id for line in self.release_line_ids]
        data_lst = []
        current_line_ids = []
        common_sp = []
        domain = []

        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.project_wbs:
            domain.append(('project_wbs', '=', self.project_wbs.id))
        if self.sub_project:
            domain.append(('sub_project', '=', self.sub_project.id))
        if self.contractor_id:
            domain.append(('partner_id', '=', self.contractor_id.id))
        if self.workorder_id:
            domain.append(('id', '=', self.workorder_id.id))

        wo_obj = self.env['work.order'].search(domain)
        data_lst = []
        for line in wo_obj:
            if (line.project_id.company_id == self.company_id):
                current_line_ids.append(line.id)
                if line.id not in old_lines:
                    """ get retention released till date """
                    released_till_date = 0
                    release_line_obj = self.release_line_ids.search([('workorder_id', '=', line.id)])

                    for release_line in release_line_obj:
                        if release_line.retention_id.stage_id == st_id:
                            released_till_date = released_till_date + release_line.current_release_amt

                    computed_retention = (line.retention * line.amount_untaxed) / 100
                    balance_retention = computed_retention - released_till_date

                    vals = {
                        'project_id': line.project_id.id,
                        'sub_project': line.sub_project.id,
                        'workorder_id': line.id,
                        'retention_id': self.id,
                        'total_retention': line.retention,
                        'wo_amount': line.amount_total,
                        'balance_retention': balance_retention,
                        'computed_retention': computed_retention,
                        'release_till_date': released_till_date
                    }
                    data_lst.append((0, 0, vals))

        common = list(set(old_lines).intersection(current_line_ids))

        for line in self.release_line_ids:
            if line.workorder_id.id not in current_line_ids:
                data_lst.append((2, line.id, False))

        val = ({'release_line_ids': data_lst})
        self.update(val)

    def unlink(self):
        for line in self.release_line_ids:
            if line.current_release_amt > line.balance_retention:
                raise UserError(_('You cannot release greater than balance retention.'))

        return models.Model.unlink(self)

    def write(self, vals):
        res = models.Model.write(self, vals)
        for line in self.release_line_ids:
            if line.current_release_amt > line.balance_retention:
                raise UserError(_('You cannot release greater than balance retention.'))

        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            rec = super(RetentionRelease, self).create(vals_list)
            context = dict(self._context or {})
            for line in self.release_line_ids:
                if line.current_release_amt > line.balance_retention:
                    raise UserError(_('You cannot release greater than balance retention.'))

            st_id = self.env['stage.master'].search([('draft', '=', True)])

            vals = {
                'date': datetime.now(),
                'from_stage': st_id.id,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'retention.release',
                'res_id': rec.id,
            }
            self.env['mail.messages'].create(vals)

            return rec


class RetentionLine(models.Model):
    _name = 'release.line'
    _description = 'Retention Line'

    is_use = fields.Boolean('')
    project_id = fields.Many2one('project.project', string='Project')
    sub_project = fields.Many2one('sub.project', string='Sub Project', required=True)
    project_wbs = fields.Many2one('project.task', string='Project Wbs')
    workorder_id = fields.Many2one('work.order', 'Work Order')
    retention_id = fields.Many2one('retention.release', 'Retention')

    task_id = fields.Many2one('project.task', 'Task')
    total_retention = fields.Float('Total Retention %')
    computed_retention = fields.Float('Computed Retention')
    release_till_date = fields.Float('Retention Release Till Date %')
    balance_retention = fields.Float('Balance Retention')
    wo_amount = fields.Integer('WorkOrder Amount', default='0')
    bill_amount = fields.Integer('Bill Amount', default='0')
    current_release_amt = fields.Float('Current Release')

