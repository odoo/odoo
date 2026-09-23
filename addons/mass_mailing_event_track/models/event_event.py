from odoo import models


class EventEvent(models.Model):
    _inherit = "event.event"

    def action_mass_mailing_track_speakers(self):
        return {
            "name": "Mass Mail Attendees",
            "type": "ir.actions.act_window",
            "res_model": "mailing.mailing",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_mailing_model_id": self.env.ref(
                    "website_event_track.model_event_track"
                ).id,
                "default_mailing_domain": repr(
                    [("event_id", "in", self.ids), ("stage_id.is_cancel", "!=", True)]
                ),
                "default_subject": self.env._("Event: %s", self.name),
            },
        }
