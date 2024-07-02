# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons import base


class ResUsers(base.ResUsers):

    target_sales_invoiced = fields.Integer('Invoiced in Sales Orders Target')
