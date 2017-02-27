# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingConfiguration(models.TransientModel):
    _inherit = 'mass.mailing.config.settings'

    group_website_popup_on_exit = fields.Boolean(string="Website Popup", implied_group="website_mass_mailing.group_website_popup_on_exit")
