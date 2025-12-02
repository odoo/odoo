# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    security_lead = fields.Float(
        'Sales Safety Days', default=0.0, required=True,
        help="Margin of error for dates promised to customers. "
             "Products will be scheduled for procurement and delivery "
             "that many days earlier than the actual promised date, to "
             "cope with unexpected delays in the supply chain.")
