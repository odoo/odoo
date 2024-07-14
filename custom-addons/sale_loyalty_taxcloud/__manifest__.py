# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Account Taxcloud - Sale (loyalty)",
    'summary': """Manage discounts in taxclouds computations.""",
    'description': """
Manage discounts in taxclouds computations.
See https://taxcloud.com/support/discounts or
https://service.taxcloud.net/hc/en-us/articles/360015649791-How-can-discounts-be-applied-

Summary: all seller-provided discounts must be applied to the Sales Price before calculating sales tax.
Sellers should disclose their methodology to customers in a Discount Application Policy.

The algorithm is as follows:
 - line-specific discounts are applied first, on the lines they are supposed to apply to.
   This means product-specific discounts or discounts on the cheapest line.
 - Then global discounts are applied evenly across paid lines, as much as possible.
   If there is a remainder, it is applied sequentially, in the order of the lines,
   until there is either no discount left or no discountable line left.

Note that discount lines (with a negative price) will have no taxes applied to them,
but rather the amount of these lines will be deduced from the lines they apply to during tax computation.
    """,
    'category': 'Accounting',
    'depends': ['sale_account_taxcloud', 'sale_loyalty'],
    'auto_install': True,
    'license': 'OEEL-1',
}
