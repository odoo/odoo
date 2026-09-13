from odoo import _, exceptions, fields, models


class GamificationBadgeUserWizard(models.TransientModel):
    """Wizard for granting a badge to a user."""

    _name = "gamification.badge.user.wizard"
    _description = "Gamification User Badge Wizard"

    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
    )
    badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        required=True,
    )
    comment = fields.Text()

    def action_grant_badge(self) -> bool:
        """Grant a badge to the selected user and send a notification."""
        # This is NOT a duplicate of the guard in
        # `gamification.badge.user.create`, which reads the same but is scoped
        # `if not self.env.su`: the model exempts system grants on purpose, so
        # that challenge rewards and achievement unlocks can award badges the
        # recipient could never award themselves.  This wizard is a person
        # pressing a button, and a person may not grant themselves a badge
        # whatever rights they hold.
        BadgeUser = self.env["gamification.badge.user"]
        uid = self.env.uid
        for wiz in self:
            if uid == wiz.user_id.id:
                raise exceptions.UserError(_("You can not grant a badge to yourself."))
            BadgeUser.create(
                {
                    "user_id": wiz.user_id.id,
                    "sender_id": uid,
                    "badge_id": wiz.badge_id.id,
                    "comment": wiz.comment,
                }
            )._send_badge()
        return True
