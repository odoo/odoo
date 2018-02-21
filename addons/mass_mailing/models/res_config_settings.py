# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_mass_mailing_campaign = fields.Boolean(string="Mass Mailing Campaigns", implied_group='mass_mailing.group_mass_mailing_campaign', help="""This is useful if your marketing campaigns are composed of several emails""")
