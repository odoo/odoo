# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mass_mailing_sms, mass_mailing_sale


class UtmCampaign(mass_mailing_sale.UtmCampaign, mass_mailing_sms.UtmCampaign):

    ab_testing_sms_winner_selection = fields.Selection(selection_add=[
        ('sale_quotation_count', 'Quotations'),
        ('sale_invoiced_amount', 'Revenues'),
    ])
