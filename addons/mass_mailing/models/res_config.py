# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingConfiguration(models.TransientModel):
    _name = 'mass.mailing.config.settings'
    _inherit = 'res.config.settings'

    group_mass_mailing_campaign = fields.Selection([
        (0, "Do not organize and schedule mail campaigns (easy)"),
        (1, "Allow using marketing campaigns (advanced)")], string="Campaigns",
        implied_group='mass_mailing.group_mass_mailing_campaign',
        help="""Manage mass mailign using Campaigns""")
    group_website_popup_on_exit = fields.Selection([
        (0, 'Do not add extra content on website pages to encourage visitors to sign up'),
        (1, 'Allow the use of a pop-up snippet on website to encourage visitors to sign up on a mass mailing list')
        ], string="Website Pop-up",
        implied_group="mass_mailing.group_website_popup_on_exit")
    module_mass_mailing_themes = fields.Boolean("Mass mailing themes")
