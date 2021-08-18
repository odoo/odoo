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
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('config_id_cr_dr'):
            config_id = self.env['pos.config'].browse(self._context.get('config_id_cr_dr'))
            args += [['id', 'in', config_id.payment_method_ids.ids]]

        if self._context.get('config_jr'):
            if self._context.get('payment_method_ids') and \
                    self._context.get('payment_method_ids')[0] and \
                    self._context.get('payment_method_ids')[0][2]:
                args += [['id', 'in', self._context.get('payment_method_ids')[0][2]]]
            else:
                return False
        if self._context.get('from_delivery'):
            args += [['jr_use_for', '=', False]]
        return super(PosPaymentMethod, self).name_search(name, args=args, operator=operator, limit=limit)

    apply_charges = fields.Boolean("Apply Charges")
    fees_amount = fields.Float("Fees Amount")
    fees_type = fields.Selection(selection=[('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Fees type",
                                 default="fixed")
    optional = fields.Boolean("Optional")
    shortcut_key = fields.Char('Shortcut Key')
    jr_use_for = fields.Selection([
        ('loyalty', "Loyalty"),
        ('gift_card', "Gift Card"),
        ('gift_voucher', "Gift Voucher"),
        ('credit', "Credit"),
        ('wallet', "Wallet"),
    ], string="Method Use For",
        help='''This payment method reserve for particular feature, 
        that accounting entry will manage based on assigned features.''')
    allow_for_loyalty = fields.Boolean(string=" Allow for loyalty")

    def write(self, vals):
        if vals.get('jr_use_for') and vals.get('jr_use_for') == 'wallet':
            if vals.get('is_cash_count') or self.is_cash_count:
                raise UserError(_('You can not use cash in case of wallet !!!'))
            if not vals.get('split_transactions') or not self.split_transactions:
                raise UserError(_('Please confirm your debug mode is on & split transaction is checked !!!'))
        return super(PosPaymentMethod, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(PosPaymentMethod, self).create(vals)
        if vals.get('jr_use_for') and vals.get('jr_use_for') == 'wallet':
            if vals.get('is_cash_count'):
                raise UserError(_('You can not use cash in case of wallet !!!'))
            if not vals.get('split_transactions'):
                raise UserError(_('Please confirm your debug mode is on & split transaction is checked !!!'))
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
