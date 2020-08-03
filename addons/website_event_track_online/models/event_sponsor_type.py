# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SponsorType(models.Model):
    _inherit = "event.sponsor.type"

    display_ribbon_style = fields.Selection([
        ('no_ribbon', 'No Ribbon'),
        ('Gold', 'Gold'),
        ('Silver', 'Silver'),
        ('Bronze', 'Bronze')], string='Ribbon Style')
