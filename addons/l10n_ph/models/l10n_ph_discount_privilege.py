# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nPhDiscountPrivilege(models.Model):
    _name = "l10n_ph.discount.privilege"
    _description = "Philippines Discount Privilege"
    _order = "name, id"

    name = fields.Char(string="Discount Name", required=True)
    discount_amount = fields.Float(string="Discount Amount", required=True)
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax Applied",
        domain="[('type_tax_use', '=', 'sale'), ('company_id', 'in', [False, company_id])]",
        check_company=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        domain="[('company_ids', 'parent_of', company_id)]",
        check_company=True,
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

    _l10n_ph_discount_privilege_name_company_uniq = models.Constraint(
        "unique(name, company_id)",
        "A discount privilege with this name already exists for this company.",
    )

    @api.constrains("discount_amount")
    def _check_discount_amount(self):
        for privilege in self:
            if not (0.0 < privilege.discount_amount <= 100.0):
                raise ValidationError(
                    self.env._("Discount Amount must be between 0 and 100."),
                )
