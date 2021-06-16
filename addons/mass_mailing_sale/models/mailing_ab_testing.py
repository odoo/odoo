# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingSaleTestingCampaign(models.Model):
    _inherit = 'mailing.ab.testing'

    based_on = fields.Selection(selection_add=[
        ('sale_quotation_count', 'Quotation Count'),
        ('sale_invoiced_amount', 'Invoiced Amount'),
    ])
