from odoo import fields, models


class CalendarFilters(models.Model):
    _name = "calendar.filters"
    _description = "Calendar Filters"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Me",
        default=lambda self: self.env.user,
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Employee",
        index=True,
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)
    partner_checked = fields.Boolean(
        string="Checked",
        default=True,
    )  # used to know if the partner is checked in the filter of the calendar view for the user_id.

    _user_id_partner_id_unique = models.Constraint(
        "UNIQUE(user_id, partner_id)",
        "A user cannot have the same contact twice.",
    )

    # `unlink_from_partner_id(partner_id)` used to live here: an @api.model
    # public -- so RPC-callable -- method that unlinked the filters of *every*
    # user for a partner. Nothing in any repo called it, and with no record rule
    # on this model it let any employee wipe another's calendar overlays. The
    # rule is now `calendar_filters_rule_own`; the method is gone.
