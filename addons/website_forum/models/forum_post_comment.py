# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ForumPostMessage(models.Model):
    _name = "forum.post.comment"
    _description = "Forum Post Message"

    _order = 'create_date ASC, id ASC'

    body = fields.Html(string="Body")
    post_id = fields.Many2one("forum.post", "Post", required=True, ondelete="cascade", index=True)
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

    def _convert_to_answer(self):
        """Convert a `forum.post.comment` into an answer (`forum.post`).

        The original `forum.post.comment` is unlinked and a new answer from the
        comment's author is created. Nothing is done if the comment's author
        already answered the question.
        """
        self.ensure_one()
        post = self.post_id
        comment_sudo = self.sudo()
        # karma-based action check: must check the message's author to know if own / all
        is_author = comment_sudo.create_uid.id == self.env.user.id
        karma_own = post.forum_id.karma_comment_convert_own
        karma_all = post.forum_id.karma_comment_convert_all
        karma_convert = is_author and karma_own or karma_all
        can_convert = self.env.user.karma >= karma_convert
        if not can_convert:
            if is_author and karma_own < karma_all:
                raise AccessError(_('%d karma required to convert your comment to an answer.', karma_own))
            raise AccessError(_('%d karma required to convert a comment to an answer.', karma_all))

        # check the message's author has not already an answer
        question = post.parent_id if post.parent_id else post
        post_create_uid = comment_sudo.create_uid
        if any(answer.create_uid == post_create_uid for answer in question.child_ids):
            return False

        # create the new post
        post_values = {
            'forum_id': question.forum_id.id,
            'body': comment_sudo.body,
            'parent_id': question.id,
            'name': _('Re: %s', question.name or ''),
        }
        # done with the author user to have create_uid correctly set
        new_post = self.with_user(post_create_uid).sudo().create(post_values).sudo(False)

        # delete comment
        comment_sudo.unlink()

        return new_post

    def _notify_followers(self):
        """Notify the followers of the question / answer."""
        self.ensure_one()

        question = self.post_id.parent_id or self.post_id
        followers = self.post_id.sudo().follower_ids

        if followers:
            self.env['mail.thread'].with_context(
                email_notification_force_header=True,
                # create the mail message for Activity view on website
                mail_notify_force_create=True,
            ).message_notify(
                body=self.body,
                subject=_("New comment in %s", question.name),
                model=question._name,
                res_id=question.id,
                partner_ids=followers.ids,
                subtype_xmlid='website_forum.mt_comment_new',
                notify_author_mention=False,
            )
