# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingConfiguration(models.TransientModel):
    _name = 'mass.mailing.config.settings'
    _inherit = 'res.config.settings'

    group_mass_mailing_campaign = fields.Boolean(string="Mass Mailing Campaigns", implied_group='mass_mailing.group_mass_mailing_campaign', help="""This is useful if your marketing campaigns are composed of several emails""")
    module_mass_mailing_themes = fields.Boolean("Email Templates")
    module_website_mass_mailing = fields.Boolean("Website Call-to-Action")
    module_crm = fields.Boolean("Leads/Opportunities")
