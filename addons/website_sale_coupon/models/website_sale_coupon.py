# -*- coding: utf-8 -*-
import random
import hashlib
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from openerp import tools, models, fields, api, _


class sales_coupon_type(models.Model):
    _name = 'sales.coupon.type'
    _description = "Sales Coupon Type"

    def get_expiration_date(self, start_date):
        if self.validity_duration == 'day':
            return start_date + relativedelta(days=(self.duration))
        if self.validity_duration == 'week':
            return start_date + relativedelta(days=(self.duration * 7))
        if self.validity_duration == 'month':
            return start_date + relativedelta(months=self.duration)
        if self.validity_duration == 'year':
            return start_date + relativedelta(months=(self.duration * 12))

    name = fields.Char(string='Name', required=True)
    validity_duration = fields.Selection(
        [('day', 'Day(s)'),
         ('week', 'Week(s)'),
         ('month', 'Month(s)'),
         ('year', 'Year(s)'),
         ], string='Validity Duration', required=True, default='day',
        help="Validity Duration can be based on either day, month, week or year.")
    expiration_use = fields.Integer(
        string='Expiration Use', default='1', help="Number of Times coupon can be Used.")
    duration = fields.Integer(string="validity_duration", default='1',
                              help="Coupon valid till Duration")
    is_active = fields.Boolean(string="Active", default=True)


class sales_coupon(models.Model):
    _name = 'sales.coupon'
    _description = "Sales Coupon"
    _rec_name = "code"

    @api.onchange('coupon_type')
    def onchange_coupon_type_id(self):
        self.expiration_use = self.coupon_type.expiration_use
        self.expiration_date = self.env['sales.coupon.type'].browse([self.coupon_type.id]).get_expiration_date(fields.date.today())

    def compute_expiration(self):
        for coupon in self:
            coupon.expired_on = coupon.expiration_date if coupon.coupon_type.duration else "no limit"
            coupon.number_of_use = coupon.expiration_use if coupon.coupon_type.expiration_use else "no limit"

    @api.one
    def count_coupon(self):
        self.coupon_used = self.env['sale.order.line'].search_count(
            [('coupon_id', 'in', self.id), ('is_coupon', '=', True), ('sales_coupon_type_id', '=', False), ('product_id', '=', False)])

    code = fields.Char(string='Coupon Code',
                       default=lambda self: 'SC' +
                       (hashlib.sha1(
                           str(random.getrandbits(256)).encode('utf-8')).hexdigest()[:7]).upper(),
                       required=True, readonly=True, help="Coupon Code")
    partner_id = fields.Many2one(
        'res.partner', string='Customer')
    coupon_type = fields.Many2one('sales.coupon.type', string='Coupon Type')
    expiration_date = fields.Date(
        string='Expiration Date', help="Till this period you can use coupon")
    expired_on = fields.Char(compute="compute_expiration",
                                  string='Expiration Date', help="Till this period you can use coupon")
    expiration_use = fields.Integer(
        string='Expiration Use', help="Limit of time you can use coupon")
    number_of_use = fields.Char(compute="compute_expiration",
                                 string='Expiration Use', help="Limit of time you can use coupon")
    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    state = fields.Selection([
        ('current', 'Current'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    ], string='Status', default='current', readonly=True, select=True)
    order_line_id = fields.Many2one(
        'sale.order.line', string='Order Reference', readonly=True)
    line_id = fields.Many2one(
        'sale.order.line', string='Line', readonly=True)
    coupon_used = fields.Integer(compute="count_coupon", string="Coupon Used")

    @api.multi
    def return_action_to_open_orders(self):
        res = self.env['ir.actions.act_window'].for_xml_id(
            'website_sale_coupon', 'action_open_sale_order_line_view')
        res['domain'] = [('coupon_id', '=', self.id), (
            'is_coupon', '=', True), ('product_id', '!=', False)]
        return res

    @api.model
    def check_cron_expiration(self):
        current_coupon = self.search([('state', '=', 'current')])
        for coupon in current_coupon:
            if coupon and coupon.coupon_type.duration != 0 and (datetime.strptime(coupon.expiration_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()) < datetime.now().date():
                coupon.state = 'expired'

    @api.one
    def check_expiration(self):
        if self.state == 'used':
            return {'error': _('Coupon %s reached limit of usage.') % (self.code)}
        if self.coupon_type.duration != 0 and (datetime.strptime(self.expiration_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()) < datetime.now().date():
            self.state = 'expired'
        if self.state == 'expired':
            return {'error': _('Coupon %s  exist but is expired.') % (self.code)}

    @api.one
    def post_apply(self):
        if self.coupon_type.expiration_use != 0 and self.expiration_use <= self.coupon_used:
            self.state = 'used'
