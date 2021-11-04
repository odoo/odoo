# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError, Warning
import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser

class PosOrderInherit(models.Model):
    _inherit = "pos.order"
    _description = "inherit pos.order"

    x_total_so_pwd = fields.Float(string='PWD', store=True, readonly=True, compute='c_amount_all')
    x_balance = fields.Float(string='Balance', readonly=True, compute='c_compute_disc')
    x_date_to = fields.Date(string='Date Until', readonly=True, compute='c_compute_disc')
    x_date_from = fields.Date(string='Date From', readonly=True, compute='c_compute_disc')
    x_date_from1 = fields.Date(string='Date From', readonly=True, compute='c_compute_disc') #to be removed

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


        c_data = self.env['pos.order'].read_group([('partner_id', 'in', self.partner_id.ids), ('date_order', '>', datetime.datetime.now() - relativedelta(weeks=1, weekday=6)), ('date_order', '<=', datetime.datetime.now() - relativedelta(weeks=0, weekday=6))], ['x_total_so_pwd'], ['date_order'],
                                                    ['partner_id'])
        c_data_sd = self.env['pos.order'].read_group([('partner_id', 'in', self.partner_id.ids), ('date_order', '>', datetime.datetime.now() - relativedelta(weeks=1, weekday=6)), ('date_order', '<=',datetime.datetime.now() - relativedelta(weeks=0, weekday=6))], ['x_total_so_sd'], ['date_order'],
                                                  ['partner_id'])
        for orderr in self:
            orderr.x_balance = sum(pwd['x_total_so_pwd'] for pwd in c_data)
            orderr.x_balance_sd = sum(sd['x_total_so_sd'] for sd in c_data_sd)

        orderr.x_date_from = x_date_from  # week=0-current;week 1 -backward; -1 forward
        orderr.x_date_to = x_date_to    #weekday 6 sunday ; 0 monday(start)
        orderr.x_balance = 65 - ((orderr.x_balance)*-1)
        orderr.x_balance_sd = 65 - ((orderr.x_balance_sd) * -1)
        orderr.x_date_from1 = datetime.datetime.now() - relativedelta(weeks=1, weekday=6)  # to be removed


class PosOrderLineInherit(models.Model):
    _inherit = "pos.order.line"
    _description = "inherit Point of Sale Order Lines"

