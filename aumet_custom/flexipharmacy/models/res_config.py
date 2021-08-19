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
from ast import literal_eval
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # birthday reminder
    enable_birthday_reminder = fields.Boolean(string="Birthday Reminder")
    birthday_template_id = fields.Many2one('mail.template', string="Birthday Mail Template")
    # Auto Close POS all session
    enable_auto_close_session = fields.Boolean(string="Automatic Close Session")
    # Anniversary reminder
    enable_anniversary_reminder = fields.Boolean(string="Anniversary Reminder")
    anniversary_template_id = fields.Many2one('mail.template', string="Anniversary Template")
    # Loyalty Fields
    enable_loyalty = fields.Boolean('Loyalty')
    min_order_value = fields.Integer('Minimum Order Value')
    point_calculation = fields.Integer(string='Point Calculation')
    exclude_category = fields.Many2many('pos.category', string='Exclude Category')
    exclude_tax = fields.Boolean("Exclude Tax")
    amount_per_point = fields.Float("Amount Per Point",
                                    help="""Enter Amount to Calculate per point. E.g : If customer has 10 loyalty 
                                    points and you enter here 0.1 ,then customer gets 1 Loyalty Amount""")
    enable_customer_referral = fields.Boolean('Customer Referral')
    referral_event = fields.Selection([
        ('first_purchase', 'First Purchase'),
        ('every_purchase', 'Every Purchase')
    ], string='Refer Event')
    referral_point_calculation = fields.Integer('Referral Point Calculation')
    # generate Barcode
    gen_barcode = fields.Boolean("On Product Create Generate Barcode")
    barcode_selection = fields.Selection([('code_39', 'CODE 39'), ('code_128', 'CODE 128'),
                                          ('ean_13', 'EAN-13'), ('ean_8', 'EAN-8'),
                                          ('isbn_13', 'ISBN 13'), ('isbn_10', 'ISBN 10'),
                                          ('issn', 'ISSN'), ('upca', 'UPC-A')], string="Select Barcode Type")
    gen_internal_ref = fields.Boolean(string="On Product Create Generate Internal Reference")
    # product Expiry report
    mailsend_check = fields.Boolean(string="Send Mail")
    email_notification_days = fields.Integer(string="Expiry Alert Days")
    res_user_ids = fields.Many2many('res.users', string='Users')
    # Doctor commision
    pos_commission_calculation = fields.Selection([
        ('product', 'Product'),
        ('product_category', 'Product Category'),
        ('doctor', 'Doctor'),
    ], string='Commission Calculation ')
    pos_account_id = fields.Many2one('account.account', string='Commission Account ')
    pos_commission_based_on = fields.Selection([
        ('product_sell_price', 'Product Sell Price'),
        ('product_profit_margin', 'Product Profit Margin')
    ], string='Commission Based On ')
    pos_commission_with = fields.Selection([
        ('with_tax', 'Tax Included'),
        ('without_tax', 'Tax Excluded')
    ], string='Apply Commission With ')
    is_doctor_commission = fields.Boolean(string='Doctor Commission ')

    @api.onchange('enable_loyalty')
    def _onchange_enable_loyalty(self):
        if not self.enable_loyalty:
            self.enable_customer_referral = False

    @api.constrains('referral_point_calculation', 'point_calculation', 'min_order_value', 'amount_per_point')
    def _check_referral_point_calculation(self):
        for record in self:
            if record.referral_point_calculation == 0 and record.enable_customer_referral:
                raise ValidationError(_('Enter Referral Points.'))
            if record.point_calculation == 0 and record.enable_loyalty:
                raise ValidationError(_('Enter Points Calculation.'))
            if record.min_order_value == 0 and record.enable_loyalty:
                raise ValidationError(_('Enter Minimum Order Value.'))
            if record.amount_per_point == 0 and record.enable_loyalty:
                raise ValidationError(_('Enter Amount Per Point Value.'))

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        res_user_ids = param_obj.sudo().get_param('flexipharmacy.res_user_ids')
        if res_user_ids:
            res.update({
                'res_user_ids': literal_eval(res_user_ids),
            })
        res.update({
            'mailsend_check': self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.mailsend_check'),
            'email_notification_days': int(param_obj.sudo().get_param('flexipharmacy.email_notification_days')),
            'enable_birthday_reminder': param_obj.get_param('flexipharmacy.enable_birthday_reminder'),
            'birthday_template_id': int(param_obj.get_param('flexipharmacy.birthday_template_id')),
            'enable_anniversary_reminder': param_obj.get_param('flexipharmacy.enable_anniversary_reminder'),
            'anniversary_template_id': int(param_obj.get_param('flexipharmacy.anniversary_template_id')),
            'enable_auto_close_session': param_obj.get_param('flexipharmacy.enable_auto_close_session'),

            'enable_loyalty': param_obj.get_param('flexipharmacy.enable_loyalty'),
            'min_order_value': param_obj.get_param('flexipharmacy.min_order_value'),
            'point_calculation': param_obj.get_param('flexipharmacy.point_calculation'),
            'exclude_tax': param_obj.get_param('flexipharmacy.exclude_tax'),
            'amount_per_point': param_obj.get_param('flexipharmacy.amount_per_point'),
            'enable_customer_referral': param_obj.get_param('flexipharmacy.enable_customer_referral'),
            'referral_event': param_obj.get_param('flexipharmacy.referral_event'),
            'referral_point_calculation': param_obj.get_param('flexipharmacy.referral_point_calculation'),

            'gen_barcode': param_obj.get_param('gen_barcode'),
            'barcode_selection': param_obj.get_param('barcode_selection'),
            'gen_internal_ref': param_obj.get_param('gen_internal_ref'),
            'pos_commission_calculation' : param_obj.get_param('flexipharmacy.pos_commission_calculation'),
            'pos_commission_based_on' : param_obj.get_param('flexipharmacy.pos_commission_based_on'),
            'pos_commission_with' : param_obj.get_param('flexipharmacy.pos_commission_with'),
            'is_doctor_commission' : param_obj.get_param('flexipharmacy.is_doctor_commission'),
        })
        categories = param_obj.get_param('flexipharmacy.exclude_category')
        res.update(
            exclude_category=[(6, 0, literal_eval(categories))] if categories else False,
        )
        IrDefault = self.env['ir.default'].sudo()
        pos_account_id = IrDefault.get('res.config.settings', "pos_account_id")
        res.update({'pos_account_id': pos_account_id or False})
        return res

    def set_values(self):
        param_obj = self.env['ir.config_parameter'].sudo()
        param_obj.sudo().set_param('flexipharmacy.enable_birthday_reminder', self.enable_birthday_reminder)
        param_obj.sudo().set_param('flexipharmacy.birthday_template_id', self.birthday_template_id.id)
        param_obj.sudo().set_param('flexipharmacy.enable_anniversary_reminder', self.enable_anniversary_reminder)
        param_obj.sudo().set_param('flexipharmacy.anniversary_template_id', self.anniversary_template_id.id)
        param_obj.sudo().set_param('flexipharmacy.enable_auto_close_session', self.enable_auto_close_session)

        param_obj.sudo().set_param('flexipharmacy.enable_loyalty', self.enable_loyalty)
        param_obj.sudo().set_param('flexipharmacy.min_order_value', self.min_order_value)
        param_obj.sudo().set_param('flexipharmacy.point_calculation', self.point_calculation)
        param_obj.sudo().set_param('flexipharmacy.exclude_tax', self.exclude_tax)
        param_obj.sudo().set_param('flexipharmacy.amount_per_point', self.amount_per_point)
        param_obj.sudo().set_param('flexipharmacy.enable_customer_referral', self.enable_customer_referral)
        param_obj.sudo().set_param('flexipharmacy.referral_event', self.referral_event)
        param_obj.sudo().set_param('flexipharmacy.referral_point_calculation', self.referral_point_calculation)
        param_obj.sudo().set_param('flexipharmacy.exclude_category', self.exclude_category.ids)

        param_obj.sudo().set_param('gen_barcode', self.gen_barcode)
        param_obj.sudo().set_param('barcode_selection', self.barcode_selection)
        param_obj.sudo().set_param('gen_internal_ref', self.gen_internal_ref)
        param_obj.sudo().set_param("flexipharmacy.pos_commission_calculation", self.pos_commission_calculation)
        param_obj.sudo().set_param("flexipharmacy.pos_commission_based_on", self.pos_commission_based_on)
        param_obj.sudo().set_param("flexipharmacy.pos_commission_with", self.pos_commission_with)
        param_obj.sudo().set_param("flexipharmacy.is_doctor_commission", self.is_doctor_commission)
        param_obj.sudo().set_param('flexipharmacy.mailsend_check', self.mailsend_check)
        param_obj.sudo().set_param('flexipharmacy.res_user_ids', self.res_user_ids.ids)
        param_obj.sudo().set_param('flexipharmacy.email_notification_days', self.email_notification_days)
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "pos_account_id", self.pos_account_id.id)
        return super(ResConfigSettings, self).set_values()

    @api.model
    def load_loyalty_config_settings(self):
        record = {}

        min_order_value = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.min_order_value')])
        if min_order_value:
            record['min_order_value'] = min_order_value.value

        point_calculation = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.point_calculation')])
        if point_calculation:
            record['point_calculation'] = point_calculation.value

        exclude_tax = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.exclude_tax')])
        if exclude_tax:
            record['exclude_tax'] = exclude_tax.value

        amount_per_point = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.amount_per_point')])
        if amount_per_point:
            record['amount_per_point'] = amount_per_point.value

        enable_customer_referral = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.enable_customer_referral')])
        if enable_customer_referral:
            record['enable_customer_referral'] = enable_customer_referral.value

        referral_event = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.referral_event')])
        if referral_event:
            record['referral_event'] = referral_event.value

        referral_point_calculation = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.referral_point_calculation')])
        if referral_point_calculation:
            record['referral_point_calculation'] = referral_point_calculation.value

        enable_loyalty = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.enable_loyalty')])
        if enable_loyalty:
            record['enable_loyalty'] = enable_loyalty.value

        exclude_category = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'flexipharmacy.exclude_category')])
        if exclude_category:
            record['exclude_category'] = literal_eval(exclude_category.value)
        return [record]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
