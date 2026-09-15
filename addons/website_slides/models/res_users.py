from odoo import _, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._enroll_in_group_channels()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "group_ids" in vals:
            self._enroll_in_group_channels()
        return res

    def _enroll_in_group_channels(self):
        if not self.all_group_ids:
            return
        channels = (
            self.env["slide.channel"]
            .sudo()
            .search([("enroll_group_ids", "in", self.all_group_ids.ids)])
        )
        for user in self:
            matching = channels.filtered(
                lambda channel, user=user: channel.enroll_group_ids & user.all_group_ids
            )
            if matching:
                matching._action_add_members(user.partner_id)

    def prepare_rank_email_links(self):
        res = super().prepare_rank_email_links()
        res.append({"url": "/slides", "label": _("See our eLearning")})
        return res
