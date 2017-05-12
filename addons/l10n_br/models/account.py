# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTaxTemplate(models.Model):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax.template'

    tax_discount = fields.Boolean(string='Discount this Tax in Prince',
                                    help="Mark it for (ICMS, PIS e etc.).")
    base_reduction = fields.Float(string='Redution', digits=0, required=True,
                                    help="Um percentual decimal em % entre 0-1.", default=0)
    amount_mva = fields.Float(string='MVA Percent', digits=0, required=True,
                                help="Um percentual decimal em % entre 0-1.", default=0)
    amount_type = fields.Selection([('group', 'Group of Taxes'),
                                       ('fixed', 'Fixed'),
                                       ('percent', 'Percentage of Price'),
                                       ('division', 'Percentage of Price Tax Included')],
                                      string='Tax Computation', required=True, default='percent')


class AccountTax(models.Model):
    """ Add fields used to define some brazilian taxes """
    _inherit = 'account.tax'

    tax_discount = fields.Boolean(string='Discount this Tax in Prince', 
                                  help="Mark it for (ICMS, PIS e etc.).")
    base_reduction = fields.Float(string='Redution', digits=0, required=True,
                                  help="Um percentual decimal em % entre 0-1.", default=0)
    amount_mva = fields.Float(string='MVA Percent', digits=0, required=True,
                              help="Um percentual decimal em % entre 0-1.", default=0)
    amount_type = fields.Selection([('group', 'Group of Taxes'),
                                     ('fixed', 'Fixed'),
                                     ('percent', 'Percentage of Price'),
                                     ('division', 'Percentage of Price Tax Included')],
                                    string='Tax Computation', required=True, default='percent')
