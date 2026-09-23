from odoo import _, models


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    def action_mass_mailing_attendees(self):
        domain = repr([("slide_channel_ids", "in", self.ids)])
        return {
            "name": _("Mass Mail Course Members"),
            "type": "ir.actions.act_window",
            "res_model": "mailing.mailing",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_mailing_model_id": self.env.ref("base.model_res_partner").id,
                "default_mailing_domain": domain,
            },
        }
