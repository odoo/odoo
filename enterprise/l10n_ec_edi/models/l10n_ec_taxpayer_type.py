# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nEcTaxpayerType(models.Model):
    _name = 'l10n_ec.taxpayer.type'
    _description = "Taxpayer Type"
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(
        string="Name",
        translate=True,
        required=True,
    )
    profit_withhold_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Profit Withhold",
        company_dependent=True,
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase')],
        help="This tax is suggested on vendors withhold wizard based on prevalence. "
        "The profit withhold prevalence order is payment method (credit cards retains 0%), this taxpayer type, then product, finally fallback on account settings"
    )
    vat_goods_withhold_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Goods VAT Withhold",
        company_dependent=True,
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_vat_purchase')],
        help="This tax is suggested on vendors withhold wizard for consumable and stockable products, if not set no vat withhold is suggested"
    )
    vat_services_withhold_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Services VAT Withhold",
        company_dependent=True,
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_vat_purchase')],
        help="This tax is suggested on vendors withhold wizard for services, if not set no vat withhold is suggested"
    )
    active = fields.Boolean(default=True)
