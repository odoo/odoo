# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingCRMTestingCampaign(models.Model):
    _inherit = 'mailing.ab.testing'

    based_on = fields.Selection(selection_add=[('crm_lead_count', 'Leads/Opportunities Count')])
