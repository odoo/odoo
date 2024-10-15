# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mass_mailing, crm


class UtmCampaign(crm.UtmCampaign, mass_mailing.UtmCampaign):

    ab_testing_winner_selection = fields.Selection(selection_add=[('crm_lead_count', 'Leads')])
