from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    birthdate = fields.Date(index="btree_not_null")
    age = fields.Integer(
        compute="_compute_age",
        search="_search_age",
        # Not "avg", and not the Integer default of "sum": the client asks the
        # server for `<field>:<aggregator>` for every aggregatable field a view
        # holds, and this one is not stored, so any answer but None turns a
        # grouped list containing it into a 500.
        aggregator=None,
    )
    age_range_id = fields.Many2one(
        comodel_name="res.partner.age.range",
        compute="_compute_age_range_id",
        store=True,
        index="btree_not_null",
        group_expand="_read_group_expand_full",
    )

    _birthday = models.Index(
        "(date_part('month', birthdate), date_part('day', birthdate)) "
        "WHERE birthdate IS NOT NULL"
    )

    @api.depends("birthdate")
    def _compute_age(self) -> None:
        today = fields.Date.today()
        for partner in self:
            partner.age = (
                relativedelta(today, partner.birthdate).years
                if partner.birthdate
                else False
            )

    @api.model
    def _latest_birthdate_for_age(self, age):
        """The newest birthdate that has already completed ``age`` years."""
        return fields.Date.today() - relativedelta(years=age)

    @api.model
    def _search_age(self, operator, value):
        if operator not in ("<", "<=", ">", ">=", "=", "!="):
            raise NotImplementedError(f"Unsupported operator {operator} on age.")
        if value is None or value is False:
            if operator in ("=", "!="):
                return Domain("birthdate", operator, False)
            raise UserError(self.env._("Age is searched by a whole number of years."))

        try:
            years = int(value)
        except TypeError, ValueError, OverflowError:
            years = None
        if isinstance(value, bool) or years is None or years != value:
            raise UserError(self.env._("Age is searched by a whole number of years."))

        at_least = self._latest_birthdate_for_age(years)
        over = self._latest_birthdate_for_age(years + 1)

        if operator == ">=":
            return Domain("birthdate", "<=", at_least)
        if operator == ">":
            return Domain("birthdate", "<=", over)
        if operator == "<":
            return Domain("birthdate", ">", at_least)
        if operator == "<=":
            return Domain("birthdate", ">", over)
        exactly = Domain("birthdate", ">", over) & Domain("birthdate", "<=", at_least)
        return (
            exactly if operator == "=" else ~exactly & Domain("birthdate", "!=", False)
        )

    @api.depends("birthdate")
    def _compute_age_range_id(self) -> None:
        age_ranges = self.env["res.partner.age.range"].sudo().search([])
        for partner in self:
            if partner.birthdate:
                age_range = age_ranges.filtered(
                    lambda age_range, partner=partner: age_range._is_covering(
                        partner.birthdate.year
                    )
                )[:1]
            else:
                age_range = self.env["res.partner.age.range"].browse()
            if partner.age_range_id != age_range:
                partner.age_range_id = age_range

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [
            self.env.ref("partner.partner_menu_root").id
        ]
