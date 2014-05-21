# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class MassMailingConfiguration(osv.TransientModel):
    _name = 'marketing.config.settings'
    _inherit = 'marketing.config.settings'

    _columns = {
        'group_mass_mailing_campaign': fields.boolean(
            'Manage Mass Mailing using Campaign',
            implied_group='mass_mailing.group_mass_mailing_campaign',
            help="""Manage mass mailign using Campaigns"""),
    }
