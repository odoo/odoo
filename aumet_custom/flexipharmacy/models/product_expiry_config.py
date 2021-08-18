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
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductExpiryConfig(models.Model):
    _name = "product.expiry.config"
    _description = "product expiry configuration"

    name = fields.Char(string="Name", compute="_change_name", store=True)
    no_of_days = fields.Char(string="Number Of Days")
    active = fields.Boolean(string="Active")
    block_color = fields.Char(string="Block Color")
    text_color = fields.Char(string="Text Color")

    @api.model
    def create(self, vals):
        if vals.get('no_of_days') and vals.get('no_of_days').isdigit():
            vals['name'] = 'Expire In ' + vals.get('no_of_days') + ' Days'
        else:
            raise ValidationError(_('Enter only number of days'))
        return super(ProductExpiryConfig, self).create(vals)

    @api.depends('no_of_days')
    def _change_name(self):
        for each in self:
            if each.no_of_days:
                each.name = 'Expire In ' + each.no_of_days + ' Days'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: