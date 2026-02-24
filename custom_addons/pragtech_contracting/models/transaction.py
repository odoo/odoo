# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class Transaction(models.Model):
    _name = 'transaction.transaction'
    _description = 'Transaction'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    name = fields.Char('Transaction No.', copy=False)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    project_wbs = fields.Many2one('project.task', 'project WBS Name', domain=[('is_wbs', '=', True), ('is_task', '=', False)], required=False)
    sub_project = fields.Many2one('sub.project', 'Sub Project', required=False)
    partner_id = fields.Many2one('res.partner', string='Contractor', required=True)
    work_order_id = fields.Many2one('work.order', string='Work Order', required=True)
    transaction_type = fields.Selection([('debit_note', 'Debit Note'), ('credit_note', 'Credit Note'), ('advance', 'Advance')], string='Transaction Type', required=True)
    bank_name = fields.Char("Bank Name")
    narration = fields.Char("Narration")
    transaction_remark = fields.Text(string='Transaction Remark')
    amount = fields.Integer(string="Amount")
    commencement_date = fields.Datetime('Commencement Date')
    maximum_advance = fields.Float('Maximum Advance(%)')
    wo_type = fields.Many2one('work.order.types', 'Type')
    wct_account = fields.Many2one('account.analytic.account', string='WCT Account')
    completion_date = fields.Datetime('Completion Date')
    tds_account = fields.Many2one('account.analytic.account', string='TDS Account')
    title = fields.Char('Title')
    wct_percent = fields.Float('WCT(%)')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])
    flag = fields.Boolean(' ')
    bill_count = fields.Integer(string='# of Bills', compute='get_bill_count')
    recovered_count = fields.Integer(string='# of Recoveries', compute='get_recovered_records_count')

    recovered_till_date = fields.Float('Recovered Till Date ')
    balance_amount = fields.Float('Balance Amount ', compute='get_balance_amount')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], default='draft')

    payment_id = fields.Many2one('account.payment', 'Payment')
    counter = 0

    """ Return only count of bills """

    def get_bill_count(self):
        bill_ids = []
        bill_count = 0
        st_id = self.env['stage.master'].search([('approved', '=', True)])

        if self.transaction_type == 'credit_note':
            recovery_obj = self.env['credit.recovery.line'].search([('credit_id', '=', self.id)])
            for line in recovery_obj:
                if line.bill_id.stage_id == st_id:
                    bill_ids.append(line.bill_id.id)
                    bill_count = bill_count + 1

            self.bill_count = bill_count
        elif self.transaction_type == 'advance':
            recovery_obj = self.env['advance.recovery.line'].search([('advance_id', '=', self.id)])
            for line in recovery_obj:
                if line.bill_id.stage_id == st_id:
                    bill_ids.append(line.bill_id.id)
                    bill_count = bill_count + 1

            self.bill_count = bill_count
        elif self.transaction_type == 'debit_note':
            recovery_obj = self.env['debit.recovery.line'].search([('debit_id', '=', self.id)])
            for line in recovery_obj:
                if line.bill_id.stage_id == st_id:
                    bill_ids.append(line.bill_id.id)
                    bill_count = bill_count + 1

            self.bill_count = bill_count

        action = self.env.ref('pragtech_contracting.ra_bill_action')
        return {
            'name': 'Bills',
            'domain': [('id', 'in', bill_ids)],
            'view_mode': action.view_mode,
            'res_model': 'ra.bill',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    """ Return only count of recovery ids """

    def get_recovered_records_count(self):
        recovered_count = 0
        st_id = self.env['stage.master'].search([('approved', '=', True)])
        if self.transaction_type == 'credit_note':
            self.recovered_count = self.env['credit.recovery.line'].search_count([('credit_id', '=', self.id), ('stage_id', '=', st_id.id)])
        elif self.transaction_type == 'advance':
            self.recovered_count = self.env['advance.recovery.line'].search_count([('advance_id', '=', self.id), ('stage_id', '=', st_id.id)])
        elif self.transaction_type == 'debit_note':
            self.recovered_count = self.env['debit.recovery.line'].search_count([('debit_id', '=', self.id), ('stage_id', '=', st_id.id)])

    """ Return recovery records(tree view) """

    def get_recoveries(self):
        recovery_ids = []
        st_id = self.env['stage.master'].search([('approved', '=', True)])
        if self.transaction_type == 'credit_note':
            recovery_line_obj = self.env['credit.recovery.line'].search([('credit_id', '=', self.id), ('stage_id', '=', st_id.id)])
            for line in recovery_line_obj:
                recovery_ids.append(line.credit_rev_line_id.id)

            view_id = self.env.ref('pragtech_contracting.recovery_tree_view').id
            model = 'credit.recovery'
            action = self.env.ref('pragtech_contracting.action_credit')
        elif self.transaction_type == 'debit_note':
            action = self.env.ref('pragtech_contracting.action_advance')
            recovery_line_obj = self.env['debit.recovery.line'].search([('debit_id', '=', self.id), ('stage_id', '=', st_id.id)])
            for line in recovery_line_obj:
                recovery_ids.append(line.debit_adv_line_id.id)

            view_id = self.env.ref('pragtech_contracting.recovery_tree_view').id
            model = 'advance.recovery'
        elif self.transaction_type == 'advance':
            action = self.env.ref('pragtech_contracting.action_advance')
            recovery_line_obj = self.env['advance.recovery.line'].search([('advance_id', '=', self.id), ('stage_id', '=', st_id.id)])
            for line in recovery_line_obj:
                recovery_ids.append(line.advance_recovery_line_id.id)

            view_id = self.env.ref('pragtech_contracting.recovery_tree_view').id
            model = 'advance.recovery'

        return {
            'name': 'Recoveries',
            'domain': [('id', 'in', recovery_ids)],
            'view_mode': action.view_mode,
            'res_model': model,
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    @api.depends('amount', 'recovered_till_date')
    def get_balance_amount(self):
        self.balance_amount = self.amount - self.recovered_till_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            t_type = vals.get('transaction_type')
            wo_id = vals.get('work_order_id')
            amount = vals.get('amount')
            if t_type == 'advance':
                wo_obj = self.env['work.order'].search([('id', '=', wo_id)])
                if wo_obj.maximum_advance > 0:
                    allowed_advance = (wo_obj.maximum_advance * wo_obj.amount_total) / 100
                    if amount > allowed_advance:
                        raise UserError(_('Advance amount is greater than allowed amount.'))

            rec = super(Transaction, self).create(vals_list)
            st_id = self.env['stage.master'].search([('draft', '=', True)])
            vals = {
                'date': datetime.now(),
                'from_stage': st_id.id,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'transaction.transaction',
                'res_id': rec.id,
            }
            self.env['mail.messages'].create(vals)

            return rec

    def write(self, vals):
        if vals.get('amount'):
            t_type = self.transaction_type
            wo_id = self.work_order_id.id
            amount = vals.get('amount')
            if t_type == 'advance':
                wo_obj = self.env['work.order'].search([('id', '=', wo_id)])
                if wo_obj.maximum_advance > 0:
                    allowed_advance = (wo_obj.maximum_advance * wo_obj.amount_total) / 100
                    if amount > allowed_advance:
                        raise UserError(_('Advance amount is greater than allowed amount.'))

        rec = super(Transaction, self).write(vals)

        return rec

    @api.onchange('work_order_id')
    def on_change_work_order_id(self):
        order = self.env['work.order'].search([('id', '=', self.work_order_id.id)])
        for line in order:
            self.project_id = line.project_id.id
            self.sub_project = line.sub_project.id
            self.partner_id = line.partner_id.id
            self.commencement_date = line.commencement_date
            self.maximum_advance = line.maximum_advance
            self.wo_type = line.wo_type.id
            self.wct_account = line.wct_account.id
            self.completion_date = line.completion_date
            self.tds_account = line.tds_account.id
            self.title = line.title
            self.wct_percent = line.wct_percent

    def change_state(self, context={}):
        if self.counter == 0:
            if context.get('copy') == True:
                """ Payment creation """
                payment_method = self.env['account.payment.method'].search([('name', '=', 'Manual'), ('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
                jrnl = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
                if self.transaction_type == 'advance' and payment_method and jrnl:
                    payment = self.env['account.payment'].create({
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'partner_id': self.partner_id.id,
                        'amount': self.amount,
                        'payment_method_id': payment_method.id,
                        'journal_id': jrnl.id,
                    })
                    self.payment_id = payment.id

                self.flag = True
                self.state = 'confirm'
                if self.transaction_type == 'advance':
                    self.name = self.env['ir.sequence'].next_by_code('transaction.advance') or '/'

                    """ updating advanced amount in WO """
                    self.work_order_id.advanced_amount = self.work_order_id.advanced_amount + self.amount

                if self.transaction_type == 'debit_note':
                    self.name = self.env['ir.sequence'].next_by_code('transaction.debit.note') or '/'
                    """ updating debited amount in WO """
                    self.work_order_id.debited_amount = self.work_order_id.debited_amount + self.amount

                if self.transaction_type == 'credit_note':
                    self.name = self.env['ir.sequence'].next_by_code('transaction.credit.note') or '/'
            else:
                self.flag = False
                self.state = 'draft'

            view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }

    def view_payment(self):
        view_id = self.env.ref('account.view_account_payment_form').id,
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
            'views': [(view_id, 'form')],
        }

    def unlink(self):
        for this in self:
            if this.state == 'confirm' or this.flag == True:
                raise UserError(_('Sorry ! You cannot delete approved transaction.'))

        return super(Transaction, self).unlink()
