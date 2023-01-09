# -*- coding: utf-8 -*-

from odoo import models, fields, _, api

class TransactionLog(models.Model):
    _name = 'transaction.log'
    _description = 'Transaction Logs'

    user_id = fields.Many2one('res.users', string="User")
    event_type = fields.Selection([('opening_session', 'Opening of the session'),
                                   ('closing_session', 'Closing of the session'),
                                   ('sales', 'Sales'),
                                   ('refund', 'Refund'),
                                   ('item_creation', 'Item creation'),
                                   ('customer_creation', 'Customer creation'),
                                   ('customer_updates', 'Customer updates'),
                                   ('inventory_price_discount', 'Update of inventory, prices, discount'),
                                   ('reprint_receipt', 'Reprint of Receipt'),
                                   ('xreport_generation', 'X Report Generation'),
                                   ('zreport_generation', 'Z Report Generation'),
                                   ], string='Event Type')
    date_time = fields.Datetime(string="Date Time")

    model = fields.Char(string='Model Name', required=True)
    res_id = fields.Many2oneReference(string='Record ID', help="ID of the target record in the database", model_field='model')
    reference = fields.Char(string='Reference', compute='_compute_reference', readonly=True, store=False)

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.model, res.res_id)

    def create_transaction_log(self, event_type, model, res_id):
        self.sudo().create({
            'user_id': self.env.user.id,
            'event_type': event_type,
            'model': model,
            'res_id': res_id,
            'date_time': fields.Datetime.now(),
        })

class PosSessionLog(models.Model):
    _inherit = 'pos.session'

    def write(self, values):
        res = super(PosSessionLog, self).write(values)
        if self and res and values.get('state', False) and values['state'] in ['opened', 'closed']:
            if values['state'] == 'opened':
                self.env['transaction.log'].sudo().create_transaction_log('opening_session', 'pos.session', self[0].id)
            if values['state'] == 'closed':
                self.env['transaction.log'].sudo().create_transaction_log('closing_session', 'pos.session', self[0].id)
        return res

class PosOrderInheritLog(models.Model):
    _inherit = "pos.order"

    @api.model
    def create(self, values):
        res = super(PosOrderInheritLog, self).create(values)
        for i in res:
            if i.amount_total < 0:
                self.env['transaction.log'].sudo().create_transaction_log('refund', 'pos.order', i.id)
            else:
                self.env['transaction.log'].sudo().create_transaction_log('sales', 'pos.order', i.id)
        return res

class ProductProductLog(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, values):
        res = super(ProductProductLog, self).create(values)
        for i in res:
            self.env['transaction.log'].sudo().create_transaction_log('item_creation', 'product.product', i.id)
        return res

class ResPartnerLog(models.Model):
    _inherit = "res.partner"

    @api.model
    def create(self, values):
        res = super(ResPartnerLog, self).create(values)
        for i in res:
            self.env['transaction.log'].sudo().create_transaction_log('customer_creation', 'res.partner', i.id)
        return res

    def write(self, values):
        res = super(ResPartnerLog, self).write(values)
        if self and res and values:
            self.env['transaction.log'].sudo().create_transaction_log('customer_updates', 'res.partner', self[0].id)
        return res

class CouponProgramLog(models.Model):
    _inherit = "coupon.program"

    fg_discount_type = fields.Selection([('is_pwd_discount', 'PWD Discount'), ('is_senior_discount', 'Senior Discount')], string="FG Discount Type")

    def write(self, values):
        res = super(CouponProgramLog, self).write(values)
        if self and res:
            if 'reward_type' in values or 'rule_min_quantity' in values or 'rule_minimum_amount' in values or 'discount_fixed_amount' in values or 'discount_type' in values:
                self.env['transaction.log'].sudo().create_transaction_log('inventory_price_discount', 'pos.session', self[0].id)
        return res
