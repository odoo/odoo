from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools.mail import is_html_empty


class CrmLeadLost(models.TransientModel):
    _name = "crm.lead.lost"
    _description = "Get Lost Reason"

    lead_ids = fields.Many2many(
        comodel_name="crm.lead",
        string="Leads",
        context={"active_test": False},
    )
    lost_reason_id = fields.Many2one(comodel_name="crm.lost.reason")
    lost_feedback = fields.Html(
        string="Closing Note",
        sanitize=True,
    )

    def action_lost_reason_apply(self):
        self.check_singleton()
        if not is_html_empty(self.lost_feedback):
            self.lead_ids._track_set_log_message(
                Markup('<div style="margin-bottom: 4px;"><p>%s:</p>%s<br /></div>')
                % (_("Lost Comment"), self.lost_feedback)
            )
        res = self.lead_ids.action_set_lost(lost_reason_id=self.lost_reason_id.id)
        return res
