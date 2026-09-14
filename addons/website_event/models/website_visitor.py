from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    event_registration_ids = fields.One2many(
        comodel_name="event.registration",
        inverse_name="visitor_id",
        string="Event Registrations",
        groups="event.group_event_registration_desk",
    )
    event_registration_count = fields.Integer(
        string="# Registrations",
        compute="_compute_event_registration_count",
        groups="event.group_event_registration_desk",
    )
    event_registered_ids = fields.Many2many(
        comodel_name="event.event",
        string="Registered Events",
        compute="_compute_event_registered_ids",
        search="_search_event_registered_ids",
        compute_sudo=True,
        groups="event.group_event_registration_desk",
    )

    @api.depends("partner_id", "event_registration_ids.name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for visitor in self.sudo().filtered(
            lambda v: not v.partner_id and v.event_registration_ids
        ):
            visitor.display_name = visitor.event_registration_ids[-1].name

    @api.depends("event_registration_ids")
    def _compute_event_registration_count(self):
        read_group_res = self.env["event.registration"]._read_group(
            [("visitor_id", "in", self.ids)], ["visitor_id"], ["__count"]
        )
        visitor_mapping = {visitor.id: count for visitor, count in read_group_res}
        for visitor in self:
            visitor.event_registration_count = visitor_mapping.get(visitor.id, 0)

    @api.depends("event_registration_ids.email", "event_registration_ids.phone_ids")
    def _compute_email_phone(self):
        super()._compute_email_phone()

        for visitor in self.filtered(
            lambda visitor: not visitor.email or not visitor.mobile
        ):
            linked_registrations = visitor.event_registration_ids.sorted(
                lambda reg: (reg.create_date, reg.id), reverse=False
            )
            if not visitor.email:
                visitor.email = next(
                    (reg.email for reg in linked_registrations if reg.email), False
                )
            if not visitor.mobile:
                visitor.mobile = next(
                    (
                        reg._phone_get_number().number
                        for reg in linked_registrations
                        if reg.phone_ids
                    ),
                    False,
                )

    @api.depends("event_registration_ids")
    def _compute_event_registered_ids(self):
        for visitor in self:
            all_registrations = visitor.event_registration_ids
            visitor.event_registered_ids = all_registrations.mapped("event_id")

    def _search_event_registered_ids(self, operator, operand):
        if operator in ("not in", "not any"):
            raise UserError(
                self.env._("Unsupported 'Not In' operation on visitors registrations")
            )

        all_registrations = (
            self.env["event.registration"]
            .sudo()
            .search([("event_id", operator, operand)])
        )
        if all_registrations:
            visitor_ids = all_registrations.with_context(
                active_test=False
            ).visitor_id.ids
        else:
            visitor_ids = []

        return [("id", "in", visitor_ids)]

    def _get_domain_inactive_visitors(self):
        return super()._get_domain_inactive_visitors() & Domain(
            "event_registration_ids", "=", False
        )

    def _merge_visitor(self, target):
        if not target.partner_id:
            raise ValueError("The `target` visitor should be linked to a partner.")
        registrations = self.event_registration_ids
        registrations.visitor_id = target.id
        registration_wo_partner = registrations.filtered(
            lambda registration: not registration.partner_id
        )
        if registration_wo_partner:
            registration_wo_partner.partner_id = target.partner_id
        return super()._merge_visitor(target)
