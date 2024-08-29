# -*- coding: utf-8 -*-
from odoo.addons import utm
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class UtmCampaign(models.Model, utm.UtmCampaign):

    ab_testing_winner_selection = fields.Selection(selection_add=[('crm_lead_count', 'Leads')])
