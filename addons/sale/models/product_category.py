# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_account_invoices_to_issue_id = fields.Many2one(
        'account.account', 'Invoices to be Issued Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="Account holding the accrued value of the goods delivered but not invoiced yet. "
             "With perpetual valuation, it counterbalances the stock valuation account at closing.")
    property_account_invoices_to_issue_active = fields.Boolean(
        related='property_account_invoices_to_issue_id.active', string="Invoices to be Issued Account Active")
    property_account_invoiced_not_delivered_id = fields.Many2one(
        'account.account', 'Invoiced Not Delivered Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="Account holding the accrued value of the goods invoiced but not delivered yet. "
             "With perpetual valuation, it counterbalances the stock valuation account at closing.")
    property_account_invoiced_not_delivered_active = fields.Boolean(
        related='property_account_invoiced_not_delivered_id.active', string="Invoiced Not Delivered Account Active")
