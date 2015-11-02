# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class MassMailingConfiguration(osv.TransientModel):
    _name = 'mass.mailing.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'group_mass_mailing_campaign': fields.selection([
            (0, "Do not organize and schedule mail campaigns (easy)"),
            (1, "Allow using marketing campaigns (advanced)")
            ], "Campaigns",
            implied_group='mass_mailing.group_mass_mailing_campaign',
            help="""Manage mass mailign using Campaigns"""),
        'group_website_popup_on_exit': fields.selection([
            (0, 'Do not add extra content on website pages to encourage visitors to sign up'),
            (1, 'Allow the use of a pop-up snippet on website to encourage visitors to sign up on a mass mailing list')
            ], string="Website Pop-up",
            implied_group="mass_mailing.group_website_popup_on_exit"),
        'module_mass_mailing_themes': fields.boolean("Mass mailing themes"),
    }
