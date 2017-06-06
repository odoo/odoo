# coding=utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Avoin.Systems 2016
from openerp import api, fields, models


class FinnishCompany(models.Model):
    _inherit = 'res.company'

    payment_reference_type = fields.Selection(
        [
            ('none', 'Free Reference'),
            ('fi', 'Finnish Standard Reference'),
            ('rf', 'Creditor Reference (RF)'),
        ],
        'Payment Reference Type',
        default='none',
        help='The default payment reference for sales invoices',
        required=True,
    )
