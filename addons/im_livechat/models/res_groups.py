# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Command


class ResGroups(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = "res.groups"

    def write(self, vals):
        if vals.get("user_ids"):
            operator_group = self.env.ref("im_livechat.im_livechat_group_user")
            if operator_group in self.all_implied_ids:
                operators = operator_group.all_user_ids
                result = super().write(vals)
                lost_operators = operators - operator_group.all_user_ids
                # sudo - im_livechat.channel: user manager can remove user from livechat channels
                self.env["im_livechat.channel"].sudo() \
                    .search([("user_ids", "in", lost_operators.ids)]) \
                    .write({"user_ids": [Command.unlink(operator.id) for operator in lost_operators]})
                return result
        return super().write(vals)
