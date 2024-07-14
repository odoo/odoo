# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_automatic_po_frequency = fields.Selection([
        ('manually', 'Manually'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')],
        required=True,
        default='monthly')
    commission_po_minimum = fields.Monetary("Minimum Total Amount for PO commission",
        currency_field='currency_id')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_automatic_po_frequency = fields.Selection(
        related='company_id.commission_automatic_po_frequency',
        required=True,
        readonly=False,
    )
    commission_po_minimum = fields.Monetary("Minimum Total Amount for PO commission",
        related='company_id.commission_po_minimum',
        readonly=False,
        currency_field='currency_id')
