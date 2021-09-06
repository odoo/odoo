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
from odoo import fields, models


class PosEarnLoyalty(models.Model):
    _name = 'pos.earn.loyalty'
    _description = 'Reward Points for Pos Order'

    order_no = fields.Char('Order/Ref')
    order_date = fields.Datetime('Date')
    points = fields.Integer('Points')
    partner_id = fields.Many2one('res.partner', 'Customer')
    referral_partner_id = fields.Many2one('res.partner', 'Referred By')


class PosRedeemLoyalty(models.Model):
    _name = 'pos.redeem.loyalty'
    _description = 'Redeem Points for Pos Order'

    order_no = fields.Char('Order/Ref')
    order_date = fields.Datetime('Date')
    points = fields.Integer('Points')
    points_amount = fields.Integer('Points Amount')
    partner_id = fields.Many2one('res.partner', 'Customer')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
