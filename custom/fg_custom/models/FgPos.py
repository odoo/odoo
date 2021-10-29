# -*- coding: utf-8 -*-

from odoo import models, fields, _, tools, SUPERUSER_ID, api
from odoo.exceptions import ValidationError, UserError, Warning
import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser


class PosPaymentInherit(models.Model):
    _inherit = "pos.payment"
    _description = "inherit pos.payment"

    #point_of_sale.view_pos_pos_form
    x_check_number = fields.Char("Check Number")
    x_issuing_bank = fields.Char("Issuing Bank")
    x_check_date = fields.Date("Check Date")
    x_card_number = fields.Char("Card Number")
    x_card_name = fields.Char("Card Name")
    x_gift_card_number = fields.Char("Gift Card Number")



class PosOrder(models.Model):
    _inherit = "pos.order"

    x_total_so_pwd = fields.Float(string='PWD', store=True, readonly=True, compute='c_amount_all')
    x_balance = fields.Float(string='Balance', readonly=True, compute='c_compute_disc')
    x_date_to = fields.Date(string='Date Until', readonly=True, compute='c_compute_disc')
    x_date_from = fields.Date(string='Date From', readonly=True, compute='c_compute_disc')
    x_date_from1 = fields.Date(string='Date From', readonly=True, compute='c_compute_disc')  # to be removed

    @api.depends('lines.price_subtotal', 'lines.full_product_name')
    def c_amount_all(self):
        for order in self:
            amount2 = 0.0
            for line in order.lines:
                if line.full_product_name == 'PWD' or line.full_product_name == 'Discount: PWD - On product with following taxes: ':
                    amount2 += line.price_subtotal
            order.x_total_so_pwd = amount2

    @api.depends('lines.full_product_name')
    def c_compute_disc(self):
        x_balance = 0
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
        for orderr in self:
            orderr.x_balance = sum(pwd['x_total_so_pwd'] for pwd in c_data)

        orderr.x_date_from = x_date_from  # week=0-current;week 1 -backward; -1 forward
        orderr.x_date_to = x_date_to  # weekday 6 sunday ; 0 monday(start)
        orderr.x_balance = 65 - ((orderr.x_balance) * -1)
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
            'x_gift_card_number': ui_paymentline.get('x_gift_card_number'),
        })

        return fields


class PosOrderLineInherit(models.Model):
    _inherit = "pos.order.line"
    _description = "inherit Point of Sale Order Lines"