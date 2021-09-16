# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LunchConfirmOrderWizard(models.TransientModel):
    _name = "lunch.confirm.order.wizard"
    _description = "Lunch: Confirm Order Wizard"

    order_ids = fields.Many2many("lunch.order")
    vendor_ids = fields.Many2many("lunch.supplier")
