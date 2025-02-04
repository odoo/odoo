from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    channel_id = fields.Many2one(
        "discuss.channel",
        "Live chat from which the lead was created",
        readonly=True,
        groups="base.group_erp_manager",
        index="btree_not_null",
    )
    from_livechat = fields.Boolean(compute="_compute_from_livechat", compute_sudo=True)

    @api.depends("channel_id")
    def _compute_from_livechat(self):
        for lead in self:
            lead.from_livechat = bool(lead.channel_id)

    def action_open_livechat(self):
        # sudo - discuss.channel: can read origin channel of the lead
        self.env.user._bus_send_store(self.sudo().channel_id, extra_fields={"open_chat_window": True})
