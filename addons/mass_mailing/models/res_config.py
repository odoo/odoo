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
    }
