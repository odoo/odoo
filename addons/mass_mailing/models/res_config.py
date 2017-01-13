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
    module_mass_mailing_themes = fields.Boolean("Mass mailing themes")
