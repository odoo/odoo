from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GamificationBadgeUserWizard(models.TransientModel):
    _inherit = "gamification.badge.user.wizard"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_user_id",
        compute_sudo=True,
        store=True,
        readonly=False,
    )

    def action_grant_badge(self):
        if self.env.uid == self.user_id.id:
            raise UserError(_("You can not send a badge to yourself."))
        values = {
            "user_id": self.user_id.id,
            "sender_id": self.env.uid,
            "badge_id": self.badge_id.id,
            "employee_id": self.user_id.employee_id.id,
            "comment": self.comment,
        }

        return self.env["gamification.badge.user"].create(values)._send_badge()

    @api.depends("employee_id")
    def _compute_user_id(self):
        for wizard in self:
            wizard.user_id = wizard.employee_id.user_id
