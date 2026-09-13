from odoo import fields, models


class EventRegistration(models.Model):
    _inherit = "event.registration"

    visitor_id = fields.Many2one(
        comodel_name="website.visitor",
        index="btree_not_null",
        ondelete="set null",
    )

    def _get_fields_website_registration_allowed(self):
        return {
            "name",
            "phone_ids",
            "email",
            "company_name",
            "event_id",
            "partner_id",
            "event_slot_id",
            "event_ticket_id",
        }
