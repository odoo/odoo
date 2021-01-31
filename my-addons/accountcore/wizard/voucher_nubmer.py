# -*- coding: utf-8 -*-
from odoo import api
from odoo import exceptions
from odoo import fields
from odoo import models
from ..models.main_models import Voucher
from ..models.ac_obj import ACTools
# 设置用户默认凭证编码策略向导


class NumberStaticsWizard(models.TransientModel):
    '''设置当前用户默认策略向导'''
    _name = 'accountcore.voucher_number_statics_default'
    _description = '设置用户默认凭证编码策略向导'
    voucherNumberTastics = fields.Many2one('accountcore.voucher_number_tastics',
                                           string='当前用户策略')

    @api.model
    def default_get(self, field_names):
        default = super().default_get(field_names)
        default['voucherNumberTastics'] = self.env.user.voucherNumberTastics.id
        return default

    def setVoucherNumberTastics(self):
        currentUser = self.env['res.users'].sudo().browse(self.env.uid)
        currentUser.voucherNumberTastics = self.voucherNumberTastics.id
        return True
# 设置凭证策略号向导


class SetingVoucherNumberWizard(models.TransientModel):
    '''设置凭证策略号向导'''
    _name = 'accountcore.seting_vouchers_number'
    _description = '设置凭证策略号向导'
    voucherNumberTastics = fields.Many2one('accountcore.voucher_number_tastics',
                                           '要使用的策略',
                                           required=True)
    startNumber = fields.Integer(string='从此编号开始', default=1, required=True)
    @ACTools.refuse_role_search
    # @api.model
    def setingNumber(self):
        startNumber = self.startNumber
        numberTasticsId = self.voucherNumberTastics.id
        currentUserId = self.env.uid
        currentUser = self.env['res.users'].sudo().browse(currentUserId)
        currentUser.write(
            {'voucherNumberTastics': numberTasticsId})
        vouchers = self.env['accountcore.voucher'].sudo().browse(
            self._context.get('active_ids'))
        vouchers.sorted(key=lambda r: r.voucherdate)
        if startNumber <= 0:
            startNumber = 1
        for voucher in vouchers:
            oldstr = voucher.numberTasticsContainer_str
            voucher.numberTasticsContainer_str = Voucher.getNewNumberDict(
                oldstr,
                numberTasticsId,
                startNumber)
            startNumber += 1
        return {'name': '已生成凭证编号',
                'view_mode': 'tree,form',
                'res_model': 'accountcore.voucher',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in',  self._context.get('active_ids'))]
                }
# 设置单张凭证策略号向导


class SetingVoucherNumberSingleWizard(models.TransientModel):
    '''设置单张凭证策略号向导'''
    _name = 'accountcore.seting_voucher_number_single'
    _description = '设置单张凭证策略号向导'
    voucherNumberTastics = fields.Many2one('accountcore.voucher_number_tastics',
                                           '要使用的策略',
                                           required=True)
    newNumber = fields.Integer(string='新凭证策略号', required=True)
    @api.model
    def default_get(self, field_names):
        '''获得用户的默认凭证编号策略'''
        default = super().default_get(field_names)
        if self.env.user.voucherNumberTastics:
            default['voucherNumberTastics'] = self.env.user.voucherNumberTastics.id
        return default

    @ACTools.refuse_role_search
    def setVoucherNumberSingle(self):
        '''设置单张凭证策略号'''
        newNumber = self.newNumber
        numberTasticsId = self.voucherNumberTastics.id
        currentUserId = self.env.uid
        currentUser = self.env['res.users'].sudo().browse(currentUserId)
        currentUser.write(
            {'voucherNumberTastics': self. voucherNumberTastics.id})
        voucher = self.env['accountcore.voucher'].sudo().browse(
            self._context.get('active_id'))
        if newNumber <= 0:
            newNumber = 0
        oldstr = voucher.numberTasticsContainer_str
        voucher.numberTasticsContainer_str = Voucher.getNewNumberDict(
            oldstr,
            numberTasticsId,
            newNumber)
        return True
# 设置凭证号向导


class SetingVNumberWizard(models.TransientModel):
    '''设置凭证号向导'''
    _name = 'accountcore.seting_v_number'
    _description = '设置凭证号向导'
    startNumber = fields.Integer(string='从此编号开始', default=1, required=True)
    @ACTools.refuse_role_search
    def setingNumber(self):
        startNumber = self.startNumber
        vouchers = self.env['accountcore.voucher'].sudo().browse(
            self._context.get('active_ids'))
        vouchers.sorted(key=lambda r: r.voucherdate)
        if startNumber <= 0:
            startNumber = 1
        for voucher in vouchers:
            voucher.v_number = startNumber
            startNumber += 1
        return {'name': '已生成凭证号',
                'view_mode': 'tree,form',
                'res_model': 'accountcore.voucher',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in',  self._context.get('active_ids'))]
                }

# 设置单张凭证号向导


class SetingVNumberSingleWizard(models.TransientModel):
    '''设置单张凭证号向导'''
    _name = 'accountcore.seting_v_number_single'
    _description = '设置单张凭证号向导'
    newNumber = fields.Integer(string='新凭证号', required=True)
    @ACTools.refuse_role_search
    def setVoucherNumberSingle(self):
        '''设置修改凭证号'''
        voucher = self.env['accountcore.voucher'].sudo().browse(
            self.env.context.get('active_id'))
        if self.newNumber < 0:
            voucher.v_number = 0
        else:
            voucher.v_number = self.newNumber
        return True