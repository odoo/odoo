from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class AccountAccountTag(models.Model):
    """Tag for categorizing accounts, taxes, and products."""

    _name = "account.account.tag"
    _description = "Account Tag"

    name = fields.Char(
        string="Tag Name",
        translate=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Account Tag without removing it.",
    )
    color = fields.Integer(string="Color Index")
    applicability = fields.Selection(
        selection=[
            ("accounts", "Accounts"),
            ("taxes", "Taxes"),
            ("products", "Products"),
        ],
        default="accounts",
        required=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        help="Country for which this tag is available, when applied on taxes.",
    )

    _name_src_uniq = name_uniq_index(
        "applicability",
        "country_id",
        nulls_distinct=True,
        message="A tag with the same name and applicability already exists in this country.",
    )
