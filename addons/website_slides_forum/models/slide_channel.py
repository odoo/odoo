from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    forum_id = fields.Many2one(
        comodel_name="forum.forum",
        string="Course Forum",
        index="btree_not_null",
        copy=False,
    )
    forum_total_posts = fields.Integer(
        related="forum_id.total_posts",
        string="Number of active forum posts",
    )

    _forum_uniq = models.Constraint(
        "unique (forum_id)",
        "Only one course per forum!",
    )

    def action_redirect_to_forum(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_forum.forum_post_action"
        )
        action["view_mode"] = "list"
        action["context"] = {"create": False}
        action["domain"] = [("forum_id", "=", self.forum_id.id)]

        return action

    @api.model_create_multi
    def create(self, vals_list):
        channels = super(
            SlideChannel, self.with_context(mail_create_nosubscribe=True)
        ).create(vals_list)
        _debug.lifecycle(
            "course_forums_opened", channels=channels, forums=channels.forum_id
        )
        channels.forum_id.privacy = False
        return channels

    def write(self, vals):
        old_forum = self.forum_id

        res = super().write(vals)
        if "forum_id" in vals:
            self.forum_id.privacy = False
            if old_forum != self.forum_id:
                _debug.lifecycle(
                    "previous_forum_locked",
                    channel=self,
                    old_forum=old_forum,
                    new_forum=self.forum_id,
                )
                old_forum.write(
                    {
                        "privacy": "private",
                        "authorized_group_id": self.env.ref(
                            "website_slides.group_website_slides_officer"
                        ).id,
                    }
                )
        return res
