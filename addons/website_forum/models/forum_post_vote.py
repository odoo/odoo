# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class Vote(models.Model):
    _name = 'forum.post.vote'
    _description = 'Post Vote'
    _order = 'create_date desc, id desc'

    post_id = fields.Many2one('forum.post', string='Post', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self._uid, ondelete='cascade')
    vote = fields.Selection([('1', '1'), ('-1', '-1'), ('0', '0')], string='Vote', required=True, default='1')
    create_date = fields.Datetime('Create Date', index=True, readonly=True)
    forum_id = fields.Many2one('forum.forum', string='Forum', related="post_id.forum_id", store=True, readonly=False)
    recipient_id = fields.Many2one('res.users', string='To', related="post_id.create_uid", store=True, readonly=False)

    _sql_constraints = [
        ('vote_uniq', 'unique (post_id, user_id)', "Vote already exists!"),
    ]

    def _get_karma_value(self, old_vote, new_vote, up_karma, down_karma):
        """Return the karma to add / remove based on the old vote and on the new vote."""
        karma_values = {'-1': down_karma, '0': 0, '1': up_karma}
        karma = karma_values[new_vote] - karma_values[old_vote]

        if old_vote == new_vote:
            reason = _('no changes')
        elif new_vote == '1':
            reason = _('upvoted')
        elif new_vote == '-1':
            reason = _('downvoted')
        elif old_vote == '1':
            reason = _('no more upvoted')
        else:
            reason = _('no more downvoted')

        return karma, reason

    @api.model_create_multi
    def create(self, vals_list):
        # can't modify owner of a vote
        if not self.env.is_admin():
            for vals in vals_list:
                vals.pop('user_id', None)
                vals.pop('recipient_id', None)
            self = self.with_context({k: v for k, v in self.env.context.items() if k not in ['default_user_id', 'default_recipient_id']})  # noqa: PLW0642

        votes = super(Vote, self).create(vals_list)

        for vote in votes:
            vote._check_general_rights()
            vote._check_karma_rights(vote.vote == '1')

            # karma update
            vote._vote_update_karma('0', vote.vote)
        return votes

    def write(self, values):
        # can't modify owner of a vote
        if not self.env.is_admin():
            values.pop('user_id', None)
            values.pop('recipient_id', None)

        for vote in self:
            vote._check_general_rights(values)
            vote_value = values.get('vote')
            if vote_value is not None:
                upvote = vote.vote == '-1' if vote_value == '0' else vote_value == '1'
                vote._check_karma_rights(upvote)

                # karma update
                vote._vote_update_karma(vote.vote, vote_value)

        res = super(Vote, self).write(values)
        return res

    def _check_general_rights(self, vals=None):
        if vals is None:
            vals = {}
        post = self.post_id
        if vals.get('post_id'):
            post = self.env['forum.post'].browse(vals.get('post_id'))
        if not self.env.is_admin():
            # own post check
            if self._uid == post.create_uid.id:
                raise UserError(_('It is not allowed to vote for its own post.'))
            # own vote check
            if self._uid != self.user_id.id:
                raise UserError(_('It is not allowed to modify someone else\'s vote.'))

    def _check_karma_rights(self, upvote=False):
        # karma check
        if upvote and not self.post_id.can_upvote:
            raise AccessError(_('%d karma required to upvote.', self.post_id.forum_id.karma_upvote))
        elif not upvote and not self.post_id.can_downvote:
            raise AccessError(_('%d karma required to downvote.', self.post_id.forum_id.karma_downvote))

    def _vote_update_karma(self, old_vote, new_vote):
        if self.post_id.parent_id:
            karma, reason = self._get_karma_value(
                old_vote,
                new_vote,
                self.forum_id.karma_gen_answer_upvote,
                self.forum_id.karma_gen_answer_downvote)
            source = _('Answer %s', reason)
        else:
            karma, reason = self._get_karma_value(
                old_vote,
                new_vote,
                self.forum_id.karma_gen_question_upvote,
                self.forum_id.karma_gen_question_downvote)
            source = _('Question %s', reason)
        self.recipient_id.sudo()._add_karma(karma, self.post_id, source)
