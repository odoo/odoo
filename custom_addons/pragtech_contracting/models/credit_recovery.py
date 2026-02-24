# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class CreditRecovery(models.Model):
    _name = 'credit.recovery'
    _description = 'Credit Recovery'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    counter = 0

    def change_state(self, context={}):
        if self.counter == 0:
            self.counter = self.counter + 1
            selected_lines = []

            if context.get('copy') == True:
                self.name = self.env['ir.sequence'].next_by_code('credit.recovery.independent.of.bill') or '/'

                self.flag = True
                for line in self.credit_line_ids:
                    if line.is_use:
                        selected_lines.append(line.is_use)
                        line.transaction_date = datetime.now().date()

                    if not line.is_use:
                        line.unlink()

                if len(selected_lines) == 0:
                    raise UserError(_('Please select at least one record to approve.'))

                """ Updating recovery till date in transaction """
                for adv in self.credit_line_ids:
                    adv_obj = self.env['transaction.transaction'].browse(adv.credit_id.id)

                    if (adv.this_bill_recovery <= adv.balance_amount):
                        adv_obj.recovered_till_date = adv_obj.recovered_till_date + adv.this_bill_recovery
                    else:
                        raise UserError(_('This Bill recovery cannot be greater then balance amount.'))
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

    name = fields.Char('Name')
    project_id = fields.Many2one('project.project', string='Project')
    project_wbs = fields.Many2one('project.task', 'project WBS Name', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    contractor_id = fields.Many2one('res.partner', string='Contractor')
    workorder_id = fields.Many2one('work.order', string='Work Order')
    company_id = fields.Many2one('res.company', string='Company ID', required=True)

    credit_line_ids = fields.One2many('credit.recovery.line', 'credit_rev_line_id')

    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            rec = super(CreditRecovery, self).create(vals_list)

            st_id = self.env['stage.master'].search([('draft', '=', True)])

            vals = {
                'date': datetime.now(),
                'from_stage': st_id.id,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'credit.recovery',
                'res_id': rec.id,
            }
            self.env['mail.messages'].create(vals)

            return rec

    def compute_credit(self):
        data_lst = []
        current_line_ids = []
        old_line = [line.credit_id.id for line in self.credit_line_ids]
        domain = []
        domain.append(('transaction_type', '=', 'credit_note'))
        domain.append(('state', '=', 'confirm'))
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))

        if self.project_wbs:
            domain.append(('project_wbs', '=', self.project_wbs.id))

        if self.sub_project:
            domain.append(('sub_project', '=', self.sub_project.id))

        if self.contractor_id:
            domain.append(('partner_id', '=', self.contractor_id.id))

        if self.workorder_id:
            domain.append(('work_order_id', '=', self.workorder_id.id))

        credit_note_obj = self.env['transaction.transaction'].search(domain)
        st_id = self.env['stage.master'].search([('approved', '=', True)])

        for line in credit_note_obj:
            current_line_ids.append(line.id)
            recovered_till_date = 0
            approved_recovery_obj = self.search([('stage_id', '=', st_id.id)])
            for approved_recovery in approved_recovery_obj:
                for approved_line in approved_recovery.credit_line_ids:
                    if approved_line.is_use:
                        if approved_line.credit_id.id == line.id:
                            recovered_till_date = recovered_till_date + approved_line.balance_amount

            if (line.project_id.company_id == self.company_id):
                if line.balance_amount > 0 and line.id not in old_line:
                    vals = {
                        'credit_id': line.id,
                        'credit_note_amount': line.amount,
                        'project_id': line.project_id.id,
                        'sub_project': line.sub_project.id,
                        'workorder_id': line.work_order_id.id,
                        'credit_rev_line_id': self.id,
                        'recovered_till_date': line.recovered_till_date,
                        'balance_amount': line.balance_amount
                    }
                    data_lst.append((0, 0, vals))

        for line in self.credit_line_ids:
            if line.credit_id.id not in current_line_ids:
                data_lst.append((2, line.id, False))

        val = ({'credit_line_ids': data_lst})
        self.update(val)

    def unlink(self):
        st_id = self.env['stage.master'].search([('approved', '=', True)])
        for line in self:
            if line.stage_id.id == st_id.id:
                raise UserError(_('You cannot delete approved records.'))

        return models.Model.unlink(self)


class CreditRecoveryLine(models.Model):
    _name = 'credit.recovery.line'
    _description = 'Credit Recovery Line'

    credit_id = fields.Many2one('transaction.transaction', 'Credit Note Number')
    is_use = fields.Boolean(' ')
    project_id = fields.Many2one('project.project', string='Project')
    sub_project = fields.Many2one('sub.project', string='Sub Project')
    project_wbs = fields.Many2one('project.task', string='Project Wbs')
    workorder_id = fields.Many2one('work.order', 'Work Order')

    credit_rev_line_id = fields.Many2one('credit.recovery', 'Credit recovery')

    credit_note_amount = fields.Float('Credit Note Amount ')
    recovered_till_date = fields.Float('Given Till Date ')
    balance_amount = fields.Float('Balance Amount')
    total_recovery = fields.Float('Total Recovery ')
    this_bill_recovery = fields.Float('This Bill Credit ', default=0)
    stage_id = fields.Many2one('stage.master', related='credit_rev_line_id.stage_id')
    payment_mode = fields.Selection([
        ('cheque', 'Cheque'),
        ('ddno', 'D.D.NO'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
        ('cash', 'Cash'),
    ], string='Payment Mode')
    bank_name = fields.Char("Bank name")
    transaction_date = fields.Date('Transaction Date')
    condition = fields.Boolean(' ')
    payment_refrence = fields.Char("Cheque/DD/UTR No.")
    bill_id = fields.Many2one('ra.bill', 'Bill')

