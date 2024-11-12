# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyMail(models.Model):
    _inherit = 'loyalty.mail'

    pos_report_print_id = fields.Many2one('ir.actions.report', string="Print Report", domain=[('model', '=', 'loyalty.card')],
        help="The report action to be executed when creating a coupon/gift card/loyalty card in the PoS.",
    )
