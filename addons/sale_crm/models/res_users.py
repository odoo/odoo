# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import crm


class ResUsers(crm.ResUsers):

    target_sales_invoiced = fields.Integer('Invoiced in Sales Orders Target')
