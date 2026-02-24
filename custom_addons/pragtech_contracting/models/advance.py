# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class Advance(models.Model):
    _name = 'advance.recovery'
    _description = 'Advance Recovery'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    counter = 0

    def change_state(self, context={}):
        if self.counter == 0:
            selected_lines = []

            if context.get('copy') == True:
                self.name = self.env['ir.sequence'].next_by_code('recovery.independent.of.bill') or '/'
                self.flag = True

                for line in self.advance_line_ids:
                    if line.is_use:
                        selected_lines.append(line.is_use)
                        line.transaction_date = datetime.now().date()
                    if not line.is_use:
                        line.unlink()

                for line in self.debit_adv_line_ids:
                    if line.is_use:
                        selected_lines.append(line.is_use)
                        line.transaction_date = datetime.now().date()
                    if not line.is_use:
                        line.unlink()

                if len(selected_lines) == 0:
                    raise UserError(_('Please select at least one record to approve.'))

                """ Updating recovery till date in transaction """
                for adv in self.advance_line_ids:
                    adv_obj = self.env['transaction.transaction'].browse(adv.advance_id.id)

                    if (adv.this_bill_recovery <= adv.balance_amount):
                        adv_obj.recovered_till_date = adv_obj.recovered_till_date + adv.this_bill_recovery
                    else:
                        raise UserError(_('This Bill recovery cannot be greater then balance amount.'))

                for deb in self.debit_adv_line_ids:
                    debit_obj = self.env['transaction.transaction'].browse(deb.debit_id.id)

                    if (deb.this_bill_recovery <= deb.balance_amount):
                        debit_obj.recovered_till_date = debit_obj.recovered_till_date + deb.this_bill_recovery
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
    advance_line_ids = fields.One2many('advance.recovery.line', 'advance_recovery_line_id')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])
    flag = fields.Boolean(' ')

    debit_adv_line_ids = fields.One2many('debit.recovery.line', 'debit_adv_line_id')

    total_adv_rec = fields.Float('Total Advance Received', compute='get_total')
    total_deb_rec = fields.Float('Total Debit Received', compute='get_total')
    total_payable = fields.Float('Total Payable', compute='get_total')

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

    @api.depends('advance_line_ids.balance_amount', 'advance_line_ids.is_use', 'debit_adv_line_ids.balance_amount', 'debit_adv_line_ids.is_use')
    def get_total(self):
        total = 0
        for line in self.advance_line_ids:
            if line.is_use:
                total += line.this_bill_recovery

        self.total_adv_rec = total

        total = 0
        for line in self.debit_adv_line_ids:
            if line.is_use:
                total += line.this_bill_recovery

        self.total_deb_rec = total

        self.total_payable = self.total_adv_rec + self.total_deb_rec

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            rec = super(Advance, self).create(vals_list)

            st_id = self.env['stage.master'].search([('draft', '=', True)])

            vals = {
                'date': datetime.now(),
                'from_stage': st_id.id,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'advance.recovery',
                'res_id': rec.id,
            }
            self.env['mail.messages'].create(vals)

            return rec

    def compute_advance(self):
        self.advance_line_ids.unlink()
        self.debit_adv_line_ids.unlink()
        data_lst = []
        old_line = [line for line in self.advance_line_ids]
        domain = []
        domain.append(('transaction_type', '=', 'advance'))
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

        advances = self.env['transaction.transaction'].search(domain)
        st_id = self.env['stage.master'].search([('approved', '=', True)])

        for line in advances:
            recovered_till_date = 0
            approved_recovery_obj = self.search([('stage_id', '=', st_id.id)])
            for approved_recovery in approved_recovery_obj:
                for approved_line in approved_recovery.advance_line_ids:
                    if approved_line.is_use:
                        if approved_line.advance_id.id == line.id:
                            recovered_till_date = recovered_till_date + approved_line.balance_amount

            if (line.project_id.company_id == self.company_id):
                if line.balance_amount > 0:
                    vals = {
                        'advance_id': line.id,
                        'advance_amount': line.amount,
                        'project_id': line.project_id.id,
                        'sub_project': line.sub_project.id,
                        'workorder_id': line.work_order_id.id,
                        'advance_recovery_line_id': self.id,
                        'recovered_till_date': line.recovered_till_date,
                        'balance_amount': line.balance_amount
                    }
                    self.env['advance.recovery.line'].create(vals)

        domain.remove(('transaction_type', '=', 'advance'))
        domain.append(('transaction_type', '=', 'debit_note'))

        advances = self.env['transaction.transaction'].search(domain)
        st_id = self.env['stage.master'].search([('approved', '=', True)])
        for line in advances:
            recovered_till_date = 0
            approved_recovery_obj = self.search([('stage_id', '=', st_id.id)])
            for approved_recovery in approved_recovery_obj:
                for approved_line in approved_recovery.debit_adv_line_ids:
                    if approved_line.is_use:
                        if approved_line.debit_id.id == line.id:
                            recovered_till_date = recovered_till_date + approved_line.balance_amount

            if (line.project_id.company_id == self.company_id):
                vals = {
                    'debit_id': line.id,
                    'debit_note_amount': line.amount,
                    'project_id': line.project_id.id,
                    'sub_project': line.sub_project.id,
                    'workorder_id': line.work_order_id.id,
                    'debit_adv_line_id': self.id,
                    'recovered_till_date': line.recovered_till_date,
                    'balance_amount': line.balance_amount
                }
                self.env['debit.recovery.line'].create(vals)

    def unlink(self):
        st_id = self.env['stage.master'].search([('approved', '=', True)])
        for line in self:
            if line.stage_id.id == st_id.id:
                raise UserError(_('You cannot delete approved records.'))

        return models.Model.unlink(self)


class AdvanceRecoveryLine(models.Model):
    _name = 'advance.recovery.line'
    _description = 'Advance line'

    name = fields.Char(' ')
    advance_id = fields.Many2one('transaction.transaction', 'Advance Note No')
    is_use = fields.Boolean(' ')
    project_id = fields.Many2one('project.project', string='Project')
    sub_project = fields.Many2one('sub.project', string='Sub Project')
    workorder_id = fields.Many2one('work.order', 'Work Order')
    advance_recovery_line_id = fields.Many2one('advance.recovery', 'Advance')
    bill_id = fields.Many2one('ra.bill', 'Bill')
    advance_amount = fields.Float('Advance Amount ')
    recovered_till_date = fields.Float('Recovered Till Date ')
    balance_amount = fields.Float('Balance Recovery')
    total_recovery = fields.Float('Total Recovery ')
    this_bill_recovery = fields.Float('This Bill Recovery ', default=0)

    bill_ids = fields.Many2many('ra.bill', 'bill_adv_recovery_rel', 'ad_rec_id', 'bill_id')
    adv_recoveries = fields.Many2many('advance.recovery', 'adv_rec_recovery_rel', 'ad_rec_id', 'bill_id')
    is_use = fields.Boolean(' ')

    payment_mode = fields.Selection([
        ('cheque', 'Cheque'),
        ('ddno', 'D.D.NO'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
        ('cash', 'Cash'),
    ], string='Payment Mode')
    bank_name = fields.Char("Bank name")
    transaction_date = fields.Date('Transaction Date')
    payment_refrence = fields.Char("Cheque/DD/UTR No.")
    stage_id = fields.Many2one('stage.master', related='advance_recovery_line_id.stage_id')

