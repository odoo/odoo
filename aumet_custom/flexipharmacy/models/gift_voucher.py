# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
import datetime
import time
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import Warning


class AsplGiftVoucher(models.Model):
    _name = 'aspl.gift.voucher'
    _description = 'Used to Store Gift Voucher.'
    _rec_name = 'voucher_code'
    _order = 'id desc'

    voucher_name = fields.Char(string="Name")
    voucher_code = fields.Char(string="Code", readonly=True)
    voucher_amount = fields.Float(string="Amount")
    minimum_purchase = fields.Float(string="Minimum Purchase")
    expiry_date = fields.Date(string="Expiry Date")
    redemption_order = fields.Integer(string="Redemption Order")
    redemption_customer = fields.Integer(string="Redemption Customer")
    is_active = fields.Boolean(string="Active", default=True)
    redeem_voucher_count = fields.Integer(string="Count", compute="_redeem_voucher_total_count")

    @api.model
    def create(self, vals):
        if vals.get('expiry_date'):
            expiry_date = datetime.strptime(vals.get('expiry_date'), '%Y-%m-%d').date()
            if datetime.now().date() > expiry_date:
                raise Warning(_("Expiry Date should be greater  than today's date!"))
        if vals.get('minimum_purchase') <= 0:
            raise Warning(_('Minimum purchase should not be less then 0 amount'))
        if vals.get('minimum_purchase') >= vals.get('voucher_amount'):
            sequence_code = self.random_card_no()
            vals.update({'voucher_code': sequence_code})
            return super(AsplGiftVoucher, self).create(vals)
        else:
            raise Warning(_("Minimum purchase amount can't be less then the voucher amount"))

    @staticmethod
    def random_card_no():
        return int(time.time())

    def write(self, vals):
        if vals.get('expiry_date'):
            expiry_date = datetime.strptime(vals.get('expiry_date'), '%Y-%m-%d').date()
            today = datetime.now().date()
            if today > expiry_date:
                raise Warning(_("Expiry Date should be greater  than today's date!"))
        if (vals.get('minimum_purchase') or self.minimum_purchase) >= (
                vals.get('voucher_amount') or self.voucher_amount):
            vals.update({'minimum_purchase': vals.get('minimum_purchase') or self.minimum_purchase})
            res = super(AsplGiftVoucher, self).write(vals)
        else:
            raise Warning(_("Minimum purchase amount can't be less then the voucher amount"))
        return res

    def _redeem_voucher_total_count(self):
        for each in self:
            each.redeem_voucher_count = self.env['aspl.gift.voucher.redeem'].search_count([
                ('voucher_id', '=', self.id)])

    def action_view_redeem_voucher(self):
        redeem_voucher_ids = self.env['aspl.gift.voucher.redeem'].search([('voucher_id', '=', self.id)])
        return {
            'name': _('Redeem voucher'),
            'type': 'ir.actions.act_window',
            'res_model': 'aspl.gift.voucher.redeem',
            'target': 'current',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', redeem_voucher_ids.ids)]
        }

    _sql_constraints = [
        ('unique_name', 'UNIQUE(voucher_code)',
         'You can only add one time each Barcode.')
    ]


class AsplGiftVoucherRedeem(models.Model):
    _name = 'aspl.gift.voucher.redeem'
    _description = 'Used to Store Gift Voucher Redeem History.'
    _rec_name = 'voucher_id'
    _order = 'id desc'

    voucher_id = fields.Many2one('aspl.gift.voucher', string="Voucher", readonly=True)
    voucher_code = fields.Char(string="Code", readonly=True)
    order_name = fields.Char(string="Order", readonly=True)
    order_amount = fields.Float(string="Order Amount", readonly=True)
    voucher_amount = fields.Float(string="Voucher Amount", readonly=True)
    used_date = fields.Datetime(string="Used Date", readonly=True, default=fields.Datetime.now(), store=True)
    user_id = fields.Many2one("res.users", string="Sales Person", readonly=True)
    customer_id = fields.Many2one("res.partner", string="Customer", readonly=True)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
