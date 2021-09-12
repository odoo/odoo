# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import fields, models, api

class SaasModule(models.Model):
    _name = 'saas.module'
    _description = 'Class for creating Modules that one wishes to provide as a service.'

    name = fields.Char(string="Name", required=True)
    image = fields.Binary(string='Image')
    technical_name = fields.Char(string="Technical Name", required=True)
    categ_id = fields.Many2one(comodel_name="saas.module.category", string="Module Category")