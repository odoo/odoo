from odoo import api, fields, models


class EventBooth(models.Model):
    _name = "event.booth"
    _description = "Event Booth"
    _inherit = ["event.type.booth", "mixin.mail.thread", "mixin.mail.activity"]

    # owner
    event_type_id = fields.Many2one(
        required=False,
        ondelete="set null",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        index=True,
        required=True,
        ondelete="cascade",
    )
    # customer
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Renter",
        copy=False,
        tracking=True,
    )
    contact_name = fields.Char(
        string="Renter Name",
        compute="_compute_contact_name",
        store=True,
        copy=False,
        readonly=False,
    )
    contact_email = fields.Char(
        string="Renter Email",
        compute="_compute_contact_email",
        store=True,
        copy=False,
        readonly=False,
    )
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="event_booth_phone_number_rel",
        column1="booth_id",
        column2="phone_number_id",
        string="Renter Phone",
        compute="_compute_phone_ids",
        store=True,
        copy=False,
        readonly=False,
    )
    # state
    state = fields.Selection(
        selection=[("available", "Available"), ("unavailable", "Unavailable")],
        string="Status",
        default="available",
        required=True,
        group_expand=True,
        tracking=True,
    )
    is_available = fields.Boolean(
        compute="_compute_is_available",
        search="_search_is_available",
    )

    @api.depends("partner_id")
    def _compute_contact_name(self):
        for booth in self:
            if not booth.contact_name:
                booth.contact_name = booth.partner_id.name or False

    @api.depends("partner_id")
    def _compute_contact_email(self):
        for booth in self:
            if not booth.contact_email:
                booth.contact_email = booth.partner_id.email or False

    @api.depends("partner_id")
    def _compute_phone_ids(self):
        for booth in self:
            if not booth.phone_ids:
                booth.phone_ids = booth.partner_id.phone_ids._primary()

    @api.depends("state")
    def _compute_is_available(self):
        for booth in self:
            booth.is_available = booth.state == "available"

    def _search_is_available(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        return [("state", "=", "available" if operator == "in" else "unavailable")]

    @api.model_create_multi
    def create(self, vals_list):
        res = super(EventBooth, self.with_context(mail_create_nosubscribe=True)).create(
            vals_list
        )
        unavailable_booths = res.filtered(lambda booth: not booth.is_available)
        unavailable_booths._post_confirmation_message()
        return res

    def write(self, vals):
        to_confirm = self.filtered(lambda booth: booth.state == "available")
        res = super().write(vals)
        if vals.get("state") == "unavailable":
            to_confirm._action_post_confirm(vals)
        return res

    def _post_confirmation_message(self):
        for booth in self:
            booth.event_id.message_post_with_source(
                "event_booth.event_booth_booked_template",
                render_values={
                    "booth": booth,
                },
                subtype_xmlid="event_booth.mt_event_booth_booked",
            )

    def action_confirm(self, additional_values=None):
        write_vals = dict({"state": "unavailable"}, **additional_values or {})
        self.write(write_vals)

    def _action_post_confirm(self, write_vals):
        self._post_confirmation_message()
