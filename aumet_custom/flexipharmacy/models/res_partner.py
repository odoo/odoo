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
import logging
from odoo import models, fields, api, _
from datetime import date

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('wallet_lines')
    def _calc_remaining(self):
        total = 0.00
        for line in self.wallet_lines:
            total += line.credit - line.debit
        self.remaining_wallet_amount = total

    is_doctor = fields.Boolean("Is Doctor")
    wallet_lines = fields.One2many('wallet.management', 'customer_id', string="Wallet", readonly=True)
    remaining_wallet_amount = fields.Float(compute="_calc_remaining", string="Remaining Amount", readonly=True,
                                           store=True)
    date_of_birth = fields.Date(string="Date Of Birth")
    anniversary_date = fields.Date(string="Anniversary Date")

    earned_loyalty_ids = fields.One2many('pos.earn.loyalty', 'partner_id', string="Earned Loyalty")
    redeem_loyalty_ids = fields.One2many('pos.redeem.loyalty', 'partner_id', string="Redeem Loyalty")
    remaining_points = fields.Integer(string="Available Points", compute='compute_total_earned')

    @api.depends('earned_loyalty_ids', 'redeem_loyalty_ids')
    def compute_total_earned(self):
        for each in self:
            total_earned = sum(each.earned_loyalty_ids.mapped("points"))
            total_redeem = sum(each.redeem_loyalty_ids.mapped("points"))
            each.remaining_points = total_earned - total_redeem

    def _send_mail_birthday_and_anniversary(self):
        enable_birthday_reminder = self.env['ir.config_parameter'].sudo().get_param(
            'flexipharmacy.enable_birthday_reminder')
        if enable_birthday_reminder:
            partner_id = self.search([('date_of_birth', '!=', False)])
            today_date = date.today()
            birthday_tmpl = self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.birthday_template_id')
            for each in partner_id:
                if today_date.day == each.date_of_birth.day and today_date.month == each.date_of_birth.month:
                    try:
                        template_obj = self.env['mail.template'].browse(int(birthday_tmpl))
                        template_obj.send_mail(each.id, force_send=True, raise_exception=False)
                    except Exception as e:
                        _logger.error('Unable to send email for birthday %s', e)
        enable_anniversary_reminder = self.env['ir.config_parameter'].sudo().get_param(
            'flexipharmacy.enable_anniversary_reminder')
        if enable_anniversary_reminder:
            partner_id = self.search([('anniversary_date', '!=', False)])
            today_date = date.today()
            anniversary_tmpl = self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.anniversary_template_id')
            for each in partner_id:
                if today_date.day == each.anniversary_date.day and today_date.month == each.anniversary_date.month:
                    try:
                        template_obj = self.env['mail.template'].browse(int(anniversary_tmpl))
                        template_obj.send_mail(each.id, force_send=True, raise_exception=False)

                    except Exception as e:
                        _logger.error('Unable to send email for birthday %s', e)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
