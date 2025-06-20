# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ForumPostMessage(models.Model):
    _name = "forum.post.comment"
    _description = "Forum Post Message"

    _order = 'create_date ASC, id ASC'

    body = fields.Html(string="Body")
    post_id = fields.Many2one("forum.post", "Post", required=True, ondelete="cascade")
    forum_id = fields.Many2one("forum.forum", "Forum", related="post_id.forum_id")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        if not self.env.is_admin() and (message := next((record for record in records if not record.post_id.can_comment), None)):
            raise AccessError(_('%i karma required to comment.', message.post_id.karma_comment))

        return records

    def write(self, vals):
        if 'post_id' in vals:
            raise AccessError(_('Can not change the post of a comment.'))

        if not self.env.is_admin() and (message := next((record for record in self if not record.post_id.can_edit), None)):
            raise AccessError(_('%i karma required to edit a comment.', message.post_id.karma_edit))

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_enough_karma(self):
        if not self.env.is_admin() and (message := next((record for record in self if not record.post_id.can_edit), None)):
            raise AccessError(_('%i karma required to delete a comment.', message.post_id.karma_edit))

    def _notify_followers(self):
        """Notify the followers of the question / answer."""
        self.ensure_one()

        question = self.post_id.parent_id or self.post_id
        followers = self.post_id.sudo().follower_ids

        if followers:
            self.env['mail.thread'].message_notify(
                body=self.body,
                subject=_("New comment on %s", question.name),
                model=question._name,
                res_id=question.id,
                partner_ids=followers.ids,
                subtype_xmlid='website_forum.mt_comment_new',
                notify_author_mention=False,
            )
