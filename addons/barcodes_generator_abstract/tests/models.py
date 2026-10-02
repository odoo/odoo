# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

# pylint: disable=consider-merging-classes-inherited


class BarcodeRuleUserFake(models.Model):
    _inherit = "barcode.rule"

    generate_model = fields.Selection(
        selection_add=[("res.users", "Users")], ondelete={"res.users": "cascade"}
    )

    type = fields.Selection(
        selection_add=[("user", "User")], ondelete={"user": "cascade"}
    )


class BarcodeGeneratorUserFake(models.Model):
    _name = "res.users"
    _inherit = ["res.users", "barcode.generate.mixin"]

    barcode = fields.Char(copy=False)
