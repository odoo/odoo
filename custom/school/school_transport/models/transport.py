# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError


class StudentTransport(models.Model):
    _name = 'student.transport'
    _description = 'Transport Information'


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    _description = 'Driver Information'

    licence_no = fields.Char('License No')
    is_driver = fields.Boolean('IS driver', help="Check if employee is driver")
    transport_vehicle = fields.One2many('transport.vehicle',
                                        'driver_id', 'Vehicles')


class TransportPoint(models.Model):
    '''for points on root'''
    _name = 'transport.point'
    _description = 'Transport Point Information'

    name = fields.Char('Point Name', required=True)
    amount = fields.Float('Amount', default=0.0)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        name = self._context.get('name')
        if name:
            transport_obj = self.env['student.transport']
            for transport_data in transport_obj.browse(name):
                point_ids = [point_id.id
                             for point_id in transport_data.trans_point_ids]
                args.append(('id', 'in', point_ids))
        return super(TransportPoint, self)._search(
            args=args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid)


class TransportVehicle(models.Model):
    '''for vehicle detail'''

    @api.multi
    @api.depends('vehi_participants_ids')
    def _compute_participants(self):
        '''Method to get number participant'''
        for rec in self:
            rec.participant = len(rec.vehi_participants_ids)

    _name = 'transport.vehicle'
    _rec_name = 'vehicle'
    _description = 'Transport vehicle Information'

    driver_id = fields.Many2one('hr.employee', 'Driver Name', required=True)
    vehicle = fields.Char('Vehicle No', required=True)
    capacity = fields.Integer('Capacity')
    participant = fields.Integer(compute='_compute_participants',
                                 string='Total Participants', readonly=True,
                                 help="Students registered in root")
    vehi_participants_ids = fields.Many2many('transport.participant',
                                             'vehicle_participant_student_rel',
                                             'vehicle_id', 'student_id',
                                             ' vehicle Participants')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        '''Override method to get vehicles of selected transport root'''
        name = self._context.get('name')
        if name:
            transport_obj = self.env['student.transport']
            transport_data = transport_obj.browse(name)
            vehicle_ids = [std_id.id
                           for std_id in transport_data.trans_vehicle_ids]
            args.append(('id', 'in', vehicle_ids))
        return super(TransportVehicle, self)._search(
            args=args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid)


class TransportParticipant(models.Model):
    '''for participants'''
    _name = 'transport.participant'
    _rec_name = 'stu_pid_id'
    _description = 'Transport Participant Information'

    name = fields.Many2one('student.student', 'Participant Name',
                           readonly=True, required=True)
    amount = fields.Float('Amount', readonly=True)
    transport_id = fields.Many2one('student.transport', 'Transport Root',
                                   readonly=True, required=True)
    stu_pid_id = fields.Char('Personal Identification Number', required=True)
    tr_reg_date = fields.Date('Transportation Registration Date',
                              help="Start date of registration")
    tr_end_date = fields.Date('Registration End Date',
                              help="End date of registration")
    months = fields.Integer('Registration For Months')
    vehicle_id = fields.Many2one('transport.vehicle', 'Vehicle No')
    point_id = fields.Many2one('transport.point', 'Point Name',
                               help="Name of point")
    state = fields.Selection([('running', 'Running'),
                              ('over', 'Over')],
                             'State', readonly=True,)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        name = self._context.get('name')
        if name:
            student_obj = self.env['student.student']
            for student_data in student_obj.browse(name):
                transport_ids = [transport_id.id
                                 for transport_id in
                                 student_data.transport_ids]
                args.append(('id', 'in', transport_ids))
        return super(TransportParticipant, self
                     )._search(args=args, offset=offset,
                               limit=limit, count=count,
                               access_rights_uid=access_rights_uid)

    @api.multi
    def set_over(self):
        self.write({'state': 'over'})


class StudentTransports(models.Model):
    '''for root detail'''

    _name = 'student.transport'
    _description = 'Student Transport Information'

    @api.multi
    @api.depends('trans_participants_ids')
    def _compute_total_participants(self):
        for rec in self:
            rec.total_participantes = len(rec.trans_participants_ids)

    name = fields.Char('Transport Root Name', required=True)
    start_date = fields.Date('Start Date', required=True)
    contact_per_id = fields.Many2one('hr.employee', 'Contact Person',
                                     help="Contact Person")
    end_date = fields.Date('End Date', required=True)
    total_participantes = fields.Integer(compute='_compute_total_participants',
                                         method=True,
                                         string='Total Participants',
                                         readonly=True)
    trans_participants_ids = fields.Many2many('transport.participant',
                                              'transport_participant_rel',
                                              'participant_id', 'transport_id',
                                              'Participants', readonly=True)
    trans_vehicle_ids = fields.Many2many('transport.vehicle',
                                         'transport_vehicle_rel',
                                         'vehicle_id',
                                         'transport_id', ' vehicles')
    trans_point_ids = fields.Many2many('transport.point',
                                       'transport_point_rel',
                                       'point_id', 'root_id', ' Points')
    state = fields.Selection([('draft', 'Draft'),
                              ('open', 'Open'),
                              ('close', 'Close')],
                             'State', readonly=True, default='draft')

    @api.multi
    def transport_open(self):
        '''Method to change state open'''
        self.write({'state': 'open'})
        return True

    @api.multi
    def transport_close(self):
        '''Method to change state to close'''
        self.write({'state': 'close'})
        return True

    @api.multi
    def participant_expire(self):
        '''Schedular to change in participant state when registration date
            is over'''
        current_date = datetime.now()
        trans_parti = self.env['transport.participant']
        parti_obj_search = trans_parti.search([('tr_end_date', '<',
                                                current_date)])
        if parti_obj_search:
            for partitcipants in parti_obj_search:
                partitcipants.state = 'over'


class StudentStudent(models.Model):
    _inherit = 'student.student'
    _description = 'Student Information'

    transport_ids = fields.Many2many('transport.participant', 'std_transport',
                                     'trans_id', 'stud_id', 'Transport')


class TransportRegistration(models.Model):
    '''for registration'''
    _name = 'transport.registration'
    _description = 'Transport Registration'

    @api.depends('state')
    def _get_user_groups(self):
        user_group = self.env.ref('school_transport.group_transportation_user')
        grps = [group.id
                for group in self.env['res.users'].browse(self._uid).groups_id]
        if user_group.id in grps:
            self.transport_user = True

    name = fields.Many2one('student.transport', 'Transport Root Name',
                           domain=[('state', '=', 'open')], required=True)
    part_name = fields.Many2one('student.student', 'Participant Name',
                                required=True,
                                help="Student Name")
    reg_date = fields.Date('Registration Date', readonly=True,
                           help="Start Date of registration",
                           default=lambda * a:
                           time.strftime("%Y-%m-%d %H:%M:%S"))
    reg_end_date = fields.Date('Registration End Date', readonly=True,
                               help="Start Date of registration")
    for_month = fields.Integer('Registration For Months')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm'),
                              ('pending', 'Pending'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancel')], 'State', readonly=True,
                             default='draft')
    vehicle_id = fields.Many2one('transport.vehicle', 'Vehicle No',
                                 required=True)
    point_id = fields.Many2one('transport.point', 'Point', widget='selection',
                               required=True)
    m_amount = fields.Float('Monthly Amount', readonly=True)
    paid_amount = fields.Float('Paid Amount',
                               help="Amount Paid")
    remain_amt = fields.Float('Due Amount',
                              help="Amount Remaining")
    transport_fees = fields.Float(compute="_compute_transport_fees",
                                  string="Transport Fees")
    amount = fields.Float('Final Amount', readonly=True)
    count_inv = fields.Integer('Invoice Count', compute="_compute_invoice")
    transport_user = fields.Boolean(compute="_get_user_groups",
                                    string="transport user")

    @api.model
    def create(self, vals):
        ret_val = super(TransportRegistration, self).create(vals)
        if ret_val:
            ret_val.onchange_point_id()
            ret_val.onchange_for_month()
        return ret_val

    @api.depends('m_amount', 'for_month')
    def _compute_transport_fees(self):
        for rec in self:
            rec.transport_fees = rec.m_amount * rec.for_month

    @api.multi
    def transport_fees_pay(self):
        '''Method to generate invoice of participant'''
        invoice_obj = self.env['account.invoice']
        for rec in self:
            rec.state = 'pending'
            partner = rec.part_name and rec.part_name.partner_id
            vals = {'partner_id': partner.id,
                    'account_id': partner.property_account_receivable_id.id,
                    'transport_student_id': rec.id}
            invoice = invoice_obj.create(vals)
            journal = invoice.journal_id
            acct_journal_id = journal.default_credit_account_id.id
            account_view_id = self.env.ref('account.invoice_form')
            line_vals = {'name': 'Transport Fees',
                         'account_id': acct_journal_id,
                         'quantity': rec.for_month,
                         'price_unit': rec.m_amount}
            invoice.write({'invoice_line_ids': [(0, 0, line_vals)]})
            return {'name': _("Pay Transport Fees"),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'view_id': account_view_id.id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'current',
                    'res_id': invoice.id,
                    'context': {}}

    @api.multi
    def view_invoice(self):
        '''Method to view invoice of participant'''
        invoice_obj = self.env['account.invoice']
        for rec in self:
            invoices = invoice_obj.search([('transport_student_id', '=',
                                            rec.id)])
            action = rec.env.ref('account.action_invoice_tree1').read()[0]
            if len(invoices) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices) == 1:
                action['views'] = [(rec.env.ref('account.invoice_form').id,
                                    'form')]
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    @api.multi
    def _compute_invoice(self):
        '''Method to compute number of invoice of participant'''
        inv_obj = self.env['account.invoice']
        for rec in self:
            rec.count_inv = inv_obj.search_count([('transport_student_id',
                                                   '=', rec.id)])

    @api.multi
    @api.onchange('point_id')
    def onchange_point_id(self):
        '''Method to get amount of point selected'''
        for rec in self:
            if rec.point_id:
                rec.m_amount = rec.point_id.amount or 0.0

    @api.multi
    @api.onchange('for_month')
    def onchange_for_month(self):
        '''Method to compute registration end date'''
        for rec in self:
            tr_start_date = time.strftime("%Y-%m-%d")
            mon = relativedelta(months=+rec.for_month)
            tr_end_date = datetime.strptime(tr_start_date, '%Y-%m-%d'
                                            ) + mon
            date = datetime.strftime(tr_end_date, '%Y-%m-%d')
            rec.reg_end_date = date

    @api.multi
    def trans_regi_cancel(self):
        '''Method to set state to cancel'''
        for rec in self:
            rec.write({'state': 'cancel'})
        return True

    @api.multi
    def trans_regi_confirm(self):
        '''Method to confirm registration'''
        trans_obj = self.env['student.transport']
        prt_obj = self.env['student.student']
        stu_prt_obj = self.env['transport.participant']
        vehi_obj = self.env['transport.vehicle']
        for rec in self:
            # registration months must one or more then one
            if rec.for_month <= 0:
                raise UserError(_('Error! Sorry Registration months must be 1'
                                  'or more then one.'))
            # First Check Is there vacancy or not
            person = int(rec.vehicle_id.participant) + 1
            if rec.vehicle_id.capacity < person:
                raise UserError(_('There is No More vacancy on this vehicle.'))

            rec.write({'state': 'confirm'})
            # calculate amount and Registration End date
            amount = rec.point_id.amount * rec.for_month
            tr_start_date = (rec.reg_date)
            month = rec.for_month
            mon1 = relativedelta(months=+month)
            tr_end_date = datetime.strptime(tr_start_date, '%Y-%m-%d') + mon1
            date = datetime.strptime(rec.name.end_date, '%Y-%m-%d')
            if tr_end_date > date:
                raise UserError(_('For this much Months\
                                  Registration is not Possible because\
                                  Root end date is Early.'))
            # make entry in Transport
            dict_prt = {'stu_pid_id': str(rec.part_name.pid),
                        'amount': amount,
                        'transport_id': rec.name.id,
                        'tr_end_date': tr_end_date,
                        'name': rec.part_name.id,
                        'months': rec.for_month,
                        'tr_reg_date': rec.reg_date,
                        'point_id': rec.point_id.id,
                        'state': 'running',
                        'vehicle_id': rec.vehicle_id.id}
            temp = stu_prt_obj.sudo().create(dict_prt)
            # make entry in Transport vehicle.
            list1 = []
            for prt in rec.vehicle_id.vehi_participants_ids:
                list1.append(prt.id)
            flag = True
            for prt in list1:
                data = stu_prt_obj.browse(prt)
                if data.name.id == rec.part_name.id:
                    flag = False
            if flag:
                list1.append(temp.id)
            vehicle_id = vehi_obj.browse(rec.vehicle_id.id)
            vehicle_id.sudo().write({'vehi_participants_ids': [(6, 0, list1)]})
            # make entry in student.
            list1 = []
            for root in rec.part_name.transport_ids:
                list1.append(root.id)
            list1.append(temp.id)
            part_name_id = prt_obj.browse(rec.part_name.id)
            part_name_id.sudo().write({'transport_ids': [(6, 0, list1)]})
            # make entry in transport.
            list1 = []
            for prt in rec.name.trans_participants_ids:
                list1.append(prt.id)
            list1.append(temp.id)
            stu_tran_id = trans_obj.browse(rec.name.id)
            stu_tran_id.sudo().write({'trans_participants_ids':
                                      [(6, 0, list1)]})
        return True


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    transport_student_id = fields.Many2one('transport.registration',
                                           string="Transport Student")


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        '''Method to compute paid amount and due amount'''
        res = super(AccountPayment, self).post()
        for rec in self:
            for invoice in rec.invoice_ids:
                vals = {}
                if invoice.transport_student_id and invoice.state == 'paid':
                    fees_payment = (invoice.transport_student_id.paid_amount +
                                    rec.amount)
                    vals = {'state': 'paid',
                            'paid_amount': fees_payment}
                elif invoice.transport_student_id and invoice.state == 'open':
                    fees_payment = (invoice.transport_student_id.paid_amount +
                                    rec.amount)
                    vals = {'status': 'pending',
                            'paid_amount': fees_payment,
                            'remain_amt': invoice.residual}
                invoice.transport_student_id.write(vals)
        return res
