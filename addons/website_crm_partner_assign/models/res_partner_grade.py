# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.published.mixin']

    partner_weight = fields.Integer('Level Weight', default=1,
        help="Gives the probability to assign a lead to this partner. (0 means no assignment.)")
