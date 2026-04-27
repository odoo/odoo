# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import html2plaintext


class KnowledgeArticleThread(models.Model):
    """
        This is the model for a comment thread linked to a `knowledge.article`. Each thread inherits
        the `mail.thread` mixin.

        These threads allow end-users to discuss specific parts of the body of a knowledge article.
        Which enables reviews, taking notes, pinging a colleague to get more information on a topic, ...

        Each initial comment starts its own thread, which will then accumulate replies, reactions, etc.
        It is also possible to mark a thread as closed so that it no longer appears inside the editor
        of the article if the conversation does not need to be continued.
    """
    _name = "knowledge.article.thread"
    _description = "Article Discussion Thread"
    _inherit = ['mail.thread']
    _mail_post_access = 'read' # if you can read, you can post a message on an article thread
    _order = 'write_date desc, id desc'
    _rec_name = 'display_name'

    _ANCHOR_TEXT_MAX_LENGTH = 1200

    article_anchor_text = fields.Text("Anchor Text",
        help="The original highlighted anchor text, giving initial context if that text is modified or removed afterwards."
    )
    article_id = fields.Many2one('knowledge.article', ondelete="cascade", readonly=True, required=True)
    is_resolved = fields.Boolean("Thread Closed", tracking=True)

    @api.depends('article_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.article_id.display_name


# ===========================================================================
#                             CRUD METHODS
# ===========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'article_anchor_text' in vals:
                article_anchor_text = html2plaintext(vals['article_anchor_text'])
                vals['article_anchor_text'] = (article_anchor_text[:self._ANCHOR_TEXT_MAX_LENGTH] + '...') \
                    if len(article_anchor_text) > self._ANCHOR_TEXT_MAX_LENGTH else article_anchor_text

        return super(KnowledgeArticleThread, self.with_context(mail_create_nolog=True)).create(vals_list)

    def write(self, vals):
        if 'is_resolved' in vals:
            self.ensure_one()
        if 'article_anchor_text' in vals:
            article_anchor_text = html2plaintext(vals['article_anchor_text'])
            vals['article_anchor_text'] = (article_anchor_text[:self._ANCHOR_TEXT_MAX_LENGTH] + '...') \
                if len(article_anchor_text) > self._ANCHOR_TEXT_MAX_LENGTH else article_anchor_text
        return super().write(vals)


# ==========================================================================
#                              THREAD OVERRIDES
# ==========================================================================

    def message_post(self, **kwargs):
        """This function overrides the 'mail.thread' message_post in order to control what portal
        users that have access to an article can post through a thread message.

        Before posting as a portal we filter what's being sent to lessen security risks. Notably
        partner_ids should be a list of ids (not the records themselves) so that we don't allow command
        executions.
        """
        self.ensure_one()
        if self.env.user._is_portal() and self.article_id.user_has_access:
            authorized_keys = {'body', 'partner_ids', 'author_id', 'attachment_ids'}
            return super().message_post(
                **{key: kwargs.get(key) for key in authorized_keys},
                message_type='comment', subtype_xmlid='mail.mt_comment'
            )
        kwargs.update({'message_type': 'comment', 'subtype_xmlid': 'mail.mt_comment'})
        return super().message_post(**kwargs)

    def _get_access_action(self, access_uid=None, force_website=False):
        self.ensure_one()
        user = self.env['res.users'].sudo().browse(access_uid) if access_uid else self.env.user
        action = {
                'type': 'ir.actions.act_url',
                'url': f'/knowledge/article/{self.article_id.id}',
            }
        if access_uid is None:
            action['target_type'] = 'public'
        if self.article_id.with_user(user).user_has_access or access_uid is None:
            return action
        return super()._get_access_action(access_uid=access_uid, force_website=force_website)

    def _notify_thread_by_email(self, message, recipients_data, **kwargs):
        """We need to override this method to set our own mail template to be sent to users that
        have been tagged inside a comment. We are using the template 'knowledge.knowledge_mail_notification_layout'
        which is a simple template comprised of the comment sent and the person that tagged the notified user.
        """
        if not kwargs.get('msg_vals', {}).get('partner_ids', []):
            return
        kwargs['msg_vals'] = {**kwargs.get('msg_vals', {}), 'email_layout_xmlid': 'knowledge.knowledge_mail_notification_layout'}

        return super()._notify_thread_by_email(message, recipients_data, **kwargs)

    def _message_compute_subject(self):
        self.ensure_one()
        return _('New Mention in %s') % self.display_name

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients_data = super()._notify_get_recipients(message, msg_vals, **kwargs)
        recipients_data = [data for data in recipients_data if data['id'] in (msg_vals or {}).get('partner_ids', [])]

        return recipients_data

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if message.model != 'knowledge.article.thread':
            return groups

        self.ensure_one()
        action = self._notify_get_action_link('controller', controller='/knowledge/thread/resolve', **msg_vals)
        user_actions = [{'url': action, 'title': _('Mark Comment as Closed')}]

        new_groups = [(
            'group_knowledge_article_thread_portal_and_users',
            lambda pdata:
                pdata['uid'] and self.article_id.with_user(pdata['uid']).user_has_access,
            {
                'actions': user_actions,
                'active': True,
                'has_button_access': True,
            }
        )]

        return new_groups + groups

    def _process_attachments_for_post(self, attachments, attachment_ids, message_values):
        self.env['ir.attachment'].browse(attachment_ids).generate_access_token()
        return super()._process_attachments_for_post(attachments, attachment_ids, message_values)
