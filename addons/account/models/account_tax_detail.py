# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountTaxDetail(models.Model):
    ''' This model is used to keep the details of the taxes computation for a single journal item.
    This is particularily necessary in some reports when we need to provide the tax details grouped by base account or
    in every EDI in which we need to provide the detail for each tax.
    '''
    _name = "account.tax.detail"
    _description = "Tax Detail"

    line_id = fields.Many2one(
        comodel_name='account.move.line',
        string="Source line of taxes",
        required=True,
        readonly=True,
        ondelete='cascade',
        help="The journal item originator of this tax detail.",
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        required=True,
        ondelete='cascade',
        domain="[('deprecated', '=', False)]",
        help="The account on which the tax amount will land.",
    )
    tax_amount = fields.Float(
        string="Tax Amount",
        help="The tax amount expressed in the company's currency but not rounded to manage the tax global rounding.",
    )
    tax_amount_currency = fields.Float(
        string="Tax Amount in Foreign Currency",
        help="The tax amount expressed in the foreign's currency but not rounded to manage the tax global rounding.",
    )
    tax_base_amount = fields.Monetary(
        string="Tax Base Amount",
        currency_field='company_currency_id',
        help="The tax base amount expressed in the company's currency.",
    )
    tax_base_amount_currency = fields.Monetary(
        string="Tax Base Amount in Foreign Currency",
        currency_field='currency_id',
        help="The tax base amount expressed in the foreign's currency.",
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        help="Taxes that apply on the base amount. This field is filled only when a previous tax is affecting the base"
             "of this one.",
    )
    tag_ids = fields.Many2many(
        comodel_name='account.account.tag',
        string="Tax Grids",
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial "
             "reports.",
    )
    tax_repartition_line_id = fields.Many2one(
        comodel_name='account.tax.repartition.line',
        string="Originator Tax Distribution Line",
        required=True,
        ondelete='cascade',
        help="Tax distribution line that caused the creation of this move line, if any.",
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Originator Tax",
        required=True,
        ondelete='cascade',
        help="The tax that has generated this tax detail. It could be a group of taxes.",
    )

    currency_id = fields.Many2one(related='line_id.currency_id')
    company_currency_id = fields.Many2one(related='line_id.company_currency_id')
