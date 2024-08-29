# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model, base.ResUsers):

    target_sales_invoiced = fields.Integer('Invoiced in Sales Orders Target')
