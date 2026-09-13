from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    event_lead_rule_id = fields.Many2one(
        comodel_name="event.lead.rule",
        string="Registration Rule",
        index="btree_not_null",
        help="Rule that created this lead",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        string="Source Event",
        index="btree_not_null",
        help="Event triggering the rule that created this lead",
    )
    registration_ids = fields.Many2many(
        comodel_name="event.registration",
        string="Source Registrations",
        groups="event.group_event_registration_desk",
        help="Registrations triggering the rule that created this lead",
    )
    registration_count = fields.Count(
        count_of="registration_ids",
        string="# Registrations",
        groups="event.group_event_registration_desk",
        help="Counter for the registrations linked to this lead",
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
