# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingConfiguration(models.TransientModel):
    _inherit = 'mass.mailing.config.settings'

    group_website_popup_on_exit = fields.Selection([
        (0, 'Do not add extra content on website pages to encourage visitors to sign up'),
        (1, 'Allow the use of a pop-up snippet on website to encourage visitors to sign up on a mass mailing list')
    ], string="Website Pop-up",
        implied_group="website_mass_mailing.group_website_popup_on_exit")
