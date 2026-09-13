from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class MixinMailThreadPhone(models.AbstractModel):
    _name = "mixin.mail.thread.phone"
    _description = "Phone Blacklist Mixin"
    _inherit = ["mixin.mail.thread"]
    _phone_search_min_length = 3

    phone_sanitized = fields.Char(
        string="Sanitized Number",
        compute="_compute_phone_sanitized",
        compute_sudo=True,
        store=True,
    )
    phone_sanitized_blacklisted = fields.Boolean(
        string="Phone Blacklisted",
        compute="_compute_blacklisted",
        search="_search_phone_sanitized_blacklisted",
        compute_sudo=True,
        store=False,
        groups="base.group_user",
    )
    phone_blacklisted = fields.Boolean(
        string="Blacklisted Phone is Phone",
        compute="_compute_blacklisted",
        compute_sudo=True,
        store=False,
        groups="base.group_user",
    )
    phone_mobile_search = fields.Char(
        string="Phone Number",
        search="_search_phone_mobile_search",
        store=False,
    )

    def _search_phone_mobile_search(self, operator, value):
        return self.env["phone.number"]._search_phone_domain(
            self._get_phone_number_fields(), operator, value
        )

    @api.depends(lambda self: self._phone_get_sanitize_triggers())
    def _compute_phone_sanitized(self):
        self._assert_phone_field()
        for record in self:
            phone = record._phone_get_number()
            record.phone_sanitized = phone.sanitized if phone.valid else False

    @api.depends("phone_sanitized")
    def _compute_blacklisted(self):
        numbers = [number for number in self.mapped("phone_sanitized") if number]
        blacklist = (
            set(
                self.env["phone.blacklist"]
                .sudo()
                .search([("number", "in", numbers)])
                .mapped("number")
            )
            if numbers
            else set()
        )
        for record in self:
            record.phone_sanitized_blacklisted = record.phone_sanitized in blacklist
            record.phone_blacklisted = record.phone_sanitized_blacklisted

    @api.model
    def _search_phone_sanitized_blacklisted(self, operator, value):
        self._assert_phone_field()
        if operator not in ("in", "not in"):
            return NotImplemented

        if operator == "in":
            query = """
                SELECT m.id
                    FROM phone_blacklist bl
                    JOIN %s m
                    ON m.phone_sanitized = bl.number AND bl.active
            """
        else:
            query = """
                SELECT m.id
                    FROM %s m
                    LEFT JOIN phone_blacklist bl
                    ON m.phone_sanitized = bl.number AND bl.active
                    WHERE bl.id IS NULL
            """
        self.env.cr.execute(query % self._table)
        res = self.env.cr.fetchall()
        return [("id", "in", [r[0] for r in res])]

    def _assert_phone_field(self):
        if not self._get_phone_number_fields():
            raise UserError(_("Invalid primary phone field on model %s", self._name))

    def _phone_get_sanitize_triggers(self):
        return [
            f"{fname}.{sub}"
            for fname in self._get_phone_number_fields()
            for sub in ("sanitized", "valid", "primary", "sequence", "type")
        ]

    def _phone_set_blacklisted(self):
        return (
            self.env["phone.blacklist"].sudo()._add([r.phone_sanitized for r in self])
        )

    def _phone_reset_blacklisted(self):
        return (
            self.env["phone.blacklist"]
            .sudo()
            ._remove([r.phone_sanitized for r in self])
        )

    def phone_action_blacklist_remove(self):
        can_access = self.env["phone.blacklist"].has_access("write")
        if can_access:
            return {
                "name": self.env._(
                    "Are you sure you want to unblacklist this Phone Number?"
                ),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "phone.blacklist.remove",
                "target": "new",
            }
        else:
            raise AccessError(
                self.env._(
                    "You do not have the access right to unblacklist phone numbers. Please contact your administrator."
                )
            )
