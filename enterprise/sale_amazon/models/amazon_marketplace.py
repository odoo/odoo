# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, exceptions, fields, models


class AmazonMarketplace(models.Model):
    _name = 'amazon.marketplace'
    _description = "Amazon Marketplace"

    name = fields.Char(string="Name", required=True, translate=True)
    api_ref = fields.Char(
        string="API Identifier", help="The Amazon-defined marketplace reference.", required=True
    )
    region = fields.Selection(
        string="Region",
        help="The Amazon region of the marketplace. Please refer to the Selling Partner API "
             "documentation to find the correct region.",
        selection=[
            ('us-east-1', "North America"),
            ('eu-west-1', "Europe"),
            ('us-west-2', "Far East"),
        ],
        default='us-east-1',
        required=True,
    )
    seller_central_url = fields.Char(
        string="Seller Central URL",
        required=True,
    )
    tax_included = fields.Boolean(
        string="Tax Included", help="Whether the price includes the tax amount or not."
    )

    _sql_constraints = [(
        'unique_api_ref',
        'UNIQUE(api_ref)',
        "There can only exist one marketplace for a given API Identifier."
    )]

    @api.ondelete(at_uninstall=False)
    def _unlink_never(self):
        raise exceptions.UserError(_("Amazon marketplaces cannot be deleted."))
