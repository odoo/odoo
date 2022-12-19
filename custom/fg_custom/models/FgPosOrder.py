# -*- coding: utf-8 -*-

from odoo import models, fields, _, tools, SUPERUSER_ID, api
from odoo.exceptions import ValidationError, UserError, Warning
import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser

class POSSession(models.Model):
    _inherit = 'pos.session'

    @api.depends('config_id')
    def name_get(self):
        return [(role.id, '%s (%s)' % (role.name,role.config_id.name)) for role in self]

class PosPaymentInherit(models.Model):
    _inherit = "pos.payment"
    _description = "inherit pos.payment"

    #point_of_sale.view_pos_pos_form
    x_check_number = fields.Char("Check Number")
    x_issuing_bank = fields.Char("Issuing Bank")
    x_check_date = fields.Date("Check Date")
    x_card_number = fields.Char("Card Number")
    x_card_name = fields.Char("Card Name")
    x_approval_no = fields.Char("Approval No.")
    x_batch_num = fields.Char("Batch Number")
    x_gift_card_number = fields.Char("Gift Card Number")
    x_gcash_refnum =  fields.Char("GCash Reference Number")
    x_gcash_customer =  fields.Char("GCash Customer")
    x_gc_voucher_no = fields.Char("Gift Check Voucher No")
    x_gc_voucher_name = fields.Char("Gift Check Voucher Name")
    x_gc_voucher_cust = fields.Char("Gift Check Customer")




    @api.model
    def _export_for_ui(self, payment):
        fields = super(PosPaymentInherit, self)._export_for_ui(payment)
        fields.update({
            'x_check_number': payment.x_check_number,
            'x_issuing_bank': payment.x_issuing_bank,
            'x_check_date': payment.x_check_date,
            'x_card_number': payment.x_card_number,
            'x_card_name': payment.x_card_name,
            'x_approval_no': payment.x_approval_no,
            'x_batch_num': payment.x_batch_num,
            'x_gift_card_number': payment.x_gift_card_number,
            'x_gcash_refnum': payment.x_gcash_refnum,
            'x_gcash_customer': payment.x_gcash_customer,
            'x_gc_voucher_no': payment.x_gc_voucher_no,
            'x_gc_voucher_name': payment.x_gc_voucher_name,
            'x_gc_voucher_cust': payment.x_gc_voucher_cust
        })

        return fields

class PosOrder(models.Model):
    _inherit = "pos.order"
    _description = "inherit pos.order"

    x_total_so_pwd = fields.Float(string='PWD', store=True, readonly=True, compute='c_amount_all')
    x_balance = fields.Float(string='Balance', readonly=True, compute='c_compute_disc')
    x_date_to = fields.Date(string='Date Until', readonly=True, compute='c_compute_disc')
    x_date_from = fields.Date(string='Date From', readonly=True, compute='c_compute_disc')
    x_date_from1 = fields.Date(string='Date From', readonly=True, compute='c_compute_disc')  # to be removed

    x_total_so_sd = fields.Float(string='SD', store=True, readonly=True, compute='c_amount_all')
    x_balance_sd = fields.Float(string='SD Balance', readonly=True, compute='c_compute_disc')

    @api.depends('lines.price_subtotal', 'lines.full_product_name')
    def c_amount_all(self):
        for order in self:
            amount2 = 0.0
            amountsd = 0.0
            for line in order.lines:
                if line.full_product_name == 'PWD' or line.full_product_name == 'Discount: PWD - On product with following taxes: ':
                    amount2 += line.price_subtotal
                if line.full_product_name == 'SD' or line.full_product_name == 'Discount: SD - On product with following taxes: ':
                    amountsd += line.price_subtotal
            order.x_total_so_pwd = amount2
            order.x_total_so_sd = amountsd

    @api.depends('lines.full_product_name')
    def c_compute_disc(self):
        x_balance = 0
        x_balance_sd = 0
        day_now = datetime.datetime.now().strftime("%A")
        if day_now == "Monday":
            x_date_to = datetime.datetime.now() - relativedelta(weeks=0, weekday=6)
            x_date_from = datetime.datetime.now() - relativedelta(weeks=0, weekday=0)
        elif day_now == "Sunday":
            x_date_to = datetime.datetime.now() - relativedelta(weeks=0, weekday=6)
            x_date_from = datetime.datetime.now() - relativedelta(weeks=1, weekday=0)
        else:
            x_date_to = datetime.datetime.now() - relativedelta(weeks=0, weekday=6)
            x_date_from = datetime.datetime.now() - relativedelta(weeks=1, weekday=0)

        c_data = self.env['pos.order'].read_group([('partner_id', 'in', self.partner_id.ids), (
        'date_order', '>', datetime.datetime.now() - relativedelta(weeks=1, weekday=6)), ('date_order', '<=',
                                                                                          datetime.datetime.now() - relativedelta(
                                                                                              weeks=0, weekday=6))],
                                                  ['x_total_so_pwd'], ['date_order'],
                                                  ['partner_id'])
        c_data_sd = self.env['pos.order'].read_group([('partner_id', 'in', self.partner_id.ids), (
        'date_order', '>', datetime.datetime.now() - relativedelta(weeks=1, weekday=6)), ('date_order', '<=',
                                                                                          datetime.datetime.now() - relativedelta(
                                                                                              weeks=0, weekday=6))],
                                                     ['x_total_so_sd'], ['date_order'],
                                                     ['partner_id'])
        for orderr in self:
            orderr.x_balance = sum(pwd['x_total_so_pwd'] for pwd in c_data)
            orderr.x_balance_sd = sum(sd['x_total_so_sd'] for sd in c_data_sd)

        orderr.x_date_from = x_date_from  # week=0-current;week 1 -backward; -1 forward
        orderr.x_date_to = x_date_to  # weekday 6 sunday ; 0 monday(start)
        orderr.x_balance = 65 - ((orderr.x_balance) * -1)
        orderr.x_balance_sd = 65 - ((orderr.x_balance_sd) * -1)
        orderr.x_date_from1 = datetime.datetime.now() - relativedelta(weeks=1, weekday=6)  # to be removed

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        fields = super(PosOrder, self)._payment_fields(order, ui_paymentline)

        fields.update({
            'x_check_number': ui_paymentline.get('x_check_number'),
            'x_issuing_bank': ui_paymentline.get('x_issuing_bank'),
            'x_check_date': ui_paymentline.get('x_check_date'),
            'x_card_number': ui_paymentline.get('x_card_number'),
            'x_card_name': ui_paymentline.get('x_card_name'),
            'x_approval_no': ui_paymentline.get('x_approval_no'),
            'x_batch_num': ui_paymentline.get('x_batch_num'),
            'x_gift_card_number': ui_paymentline.get('x_gift_card_number'),
            'x_gcash_refnum': ui_paymentline.get('x_gcash_refnum'),
            'x_gcash_customer': ui_paymentline.get('x_gcash_customer'),
            'x_gc_voucher_no': ui_paymentline.get('x_gc_voucher_no'),
            'x_gc_voucher_name': ui_paymentline.get('x_gc_voucher_name'),
            'x_gc_voucher_cust': ui_paymentline.get('x_gc_voucher_cust')
        })
        return fields

    @api.model
    def _export_for_ui(self, order):
        fields = super(PosOrder, self)._export_for_ui(order)
        fields.update({
            'x_receipt_note': order.x_receipt_note,
            'x_ext_source': order.x_ext_source,
            'x_ext_order_ref': order.x_ext_order_ref,
            'x_receipt_printed': order.x_receipt_printed,
            'x_receipt_printed_date': order.x_receipt_printed_date,
            'pos_si_trans_reference': order.pos_si_trans_reference,
            'pos_trans_reference': order.pos_trans_reference,
            'pos_refund_si_reference': order.pos_refund_si_reference,
            'pos_refunded_id': order.pos_refunded_id.pos_si_trans_reference,
            'website_order_id': order.website_order_id
        })
        return fields



    @api.model
    def _order_fields(self, order):
        fields = super(PosOrder, self)._order_fields(order)
        refunded_order_id = False;
        if order.get('pos_refunded_id', False):
            refunded_order = self.env['pos.order'].search([('id', '=', order.pos_refunded_id),('active', '=', True)])
            refunded_order_id = refunded_order.pos_si_trans_reference
        fields.update({
            'x_ext_source': order.get('x_ext_source', False),
            'x_ext_order_ref': order.get('x_ext_order_ref', False),
            'x_receipt_printed': order.get('x_receipt_printed', False),
            'x_receipt_printed_date': order.get('x_receipt_printed_date', False),
            'pos_si_trans_reference': order.get('pos_si_trans_reference', False),
            'pos_trans_reference':  order.get('pos_trans_reference', False),
            'pos_refund_si_reference':  order.get('pos_refund_si_reference', False),
            'website_order_id': order.get('website_order_id', False),
            'pos_refunded_id': refunded_order_id
        })
        return fields

    @api.model
    def create_from_ui(self, orders, draft=False):
        order_ids = []
        for order in orders:
            existing_order = False
            if 'server_id' in order['data']:
                existing_order = self.env['pos.order'].search(['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])], limit=1)
            if (existing_order and existing_order.state == 'draft') or not existing_order:
                order_ids.append(self._process_order(order, draft, existing_order))
            elif (order['data']['x_receipt_printed']):
                pos_order = existing_order
                pos_order.write({
                    'x_receipt_printed': order['data']['x_receipt_printed'],
                    'x_receipt_printed_date': order['data']['x_receipt_printed_date'],
                })
        return self.env['pos.order'].search_read(domain = [('id', 'in', order_ids)], fields = ['id', 'pos_reference'])

class PosOrderLineInherit(models.Model):
    _inherit = "pos.order.line"
    _description = "inherit Point of Sale Order Lines"