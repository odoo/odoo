# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

import logging
from odoo import fields, models
from odoo.exceptions import Warning
_logger = logging.getLogger(__name__)

class BillingHistory(models.Model):
    _name = 'user.billing.history'

    name = fields.Char(string="Entry Name")
    date = fields.Date(string="Date")
    cycle_number = fields.Char(string="Cycle")
    due_users = fields.Integer(string="Due Users")
    puchased_users = fields.Integer(string="Purchased Users")
    due_users_price = fields.Float(string="Due Users Price")
    puchase_users_price = fields.Float(string="Purchase Users Price")
    is_invoiced = fields.Boolean(string="Invoiced")
    final_price = fields.Float(string="Final User's Price")
    contract_id = fields.Many2one(comodel_name="saas.contract", string="Contract ID")