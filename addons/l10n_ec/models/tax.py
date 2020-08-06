# -*- coding: utf-8 -*-
 
import time

from odoo import api, fields, models, _
import time, datetime, calendar

class tax_group(models.Model):
    _inherit = "account.tax.group"
    _name = "account.tax.group"

    code = fields.Char(_("Code"))