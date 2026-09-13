from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    event_lead_rule_id = fields.Many2one(
        comodel_name="event.lead.rule",
        string="Registration Rule",
        help="Rule that created this lead",
        index="btree_not_null",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        string="Source Event",
        help="Event triggering the rule that created this lead",
        index="btree_not_null",
    )
    registration_ids = fields.Many2many(
        comodel_name="event.registration",
        string="Source Registrations",
        help="Registrations triggering the rule that created this lead",
        groups="event.group_event_registration_desk",
    )
    registration_count = fields.Count(
        count_of="registration_ids",
        string="# Registrations",
        help="Counter for the registrations linked to this lead",
        groups="event.group_event_registration_desk",
    )

    def _merge_dependences(self, opportunities):
        super()._merge_dependences(opportunities)

        self.sudo().write(
            {
                "registration_ids": [
                    (4, registration.id)
                    for registration in opportunities.sudo().registration_ids
                ]
            }
        )

    def _merge_get_fields(self):
        return super()._merge_get_fields() + ["event_lead_rule_id", "event_id"]
