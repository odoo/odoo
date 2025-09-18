from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerCategory(models.Model):
    _name = "res.partner.category"
    _description = "Partner Tags"
    _order = "name, id"
    _parent_store = True

    def _get_default_color(self) -> int:
        return randint(1, 11)

    name = fields.Char("Name", required=True, translate=True)
    color = fields.Integer(string="Color", default=_get_default_color, aggregator=False)
    parent_id: ResPartnerCategory = fields.Many2one(
        "res.partner.category",
        string="Category",
        index=True,
        ondelete="cascade",
    )
    child_ids: ResPartnerCategory = fields.One2many(
        "res.partner.category", "parent_id", string="Child Tags"
    )
    active = fields.Boolean(
        default=True,
        help="The active field allows you to hide the category without removing it.",
    )
    parent_path = fields.Char(index=True)
    partner_ids = fields.Many2many(
        "res.partner",
        column1="category_id",
        column2="partner_id",
        string="Partners",
        copy=False,
    )

    @api.constrains("parent_id")
    def _check_parent_id(self) -> None:
        if self._has_cycle():
            raise ValidationError(_("You can not create recursive tags."))

    @api.depends("parent_id")
    def _compute_display_name(self) -> None:
        """Return the categories' display name, including their direct
        parent by default.
        """
        for category in self:
            names = []
            current = category
            while current:
                names.append(current.name or "")
                current = current.parent_id
            category.display_name = " / ".join(reversed(names))

    @api.model
    def _search_display_name(self, operator: str, value: str) -> list:
        domain = super()._search_display_name(operator, value)
        if operator.endswith("like"):
            if operator.startswith("not"):
                return NotImplemented
            return [("id", "child_of", tuple(self._search(domain)))]
        return domain
