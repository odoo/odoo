# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nPhDiscountPrivilege(models.Model):
    _name = "l10n_ph.discount.privilege"
    _description = "Philippines Discount Privilege"
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(string="Discount Name", required=True)
    discount_amount = fields.Float(
        string="Discount Amount", required=True, digits="Discount",
    )
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        help="Fiscal position used to map taxes for this privilege. ",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
    )
    applied_to_category_ids = fields.Many2many(
        "product.category",
        string="Applies To",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean("Active", default=True)

    _l10n_ph_discount_privilege_name_company_uniq = models.Constraint(
        "unique(name, company_id)",
        "A discount privilege with this name already exists for this company.",
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_use(self):
        if self.env["account.move.line"].search_count(
            [
                ("l10n_ph_discount_privilege_id", "in", self.ids),
            ],
            limit=1,
        ):
            raise ValidationError(
                self.env._(
                    "You cannot delete a discount privilege that is currently in use on an invoice. Consider archiving it instead.",
                ),
            )

    @api.constrains("discount_amount")
    def _check_discount_amount(self):
        for privilege in self:
            if not (0 < privilege.discount_amount <= 100.0):
                raise ValidationError(
                    self.env._(
                        "Discount Amount must be greater than 0 and at most 100.",
                    ),
                )
