# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingSaleSMSTestingCampaign(models.Model):
    _inherit = 'mailing.ab.testing'

    sms_based_on = fields.Selection(selection_add=[
        ('sale_quotation_count', 'Quotation Count'),
        ('sale_invoiced_amount', 'Invoiced Amount'),
    ])
