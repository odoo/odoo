# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError


class ArticleMember(models.Model):
    _name = 'knowledge.article.member'
    _description = 'Article Member'
    _rec_name = 'partner_id'

    article_id = fields.Many2one(
        'knowledge.article', 'Article',
        ondelete='cascade', required=True)
    partner_id = fields.Many2one(
        'res.partner', 'Partner',
        index=True, ondelete='cascade', required=True)
    permission = fields.Selection(
        [('write', 'Can edit'),
         ('read', 'Can read'),
         ('none', 'No access')],
        required=True, default='read')
    article_permission = fields.Selection(
        related='article_id.inherited_permission',
        readonly=True, store=True)

    _sql_constraints = [
        ('unique_article_partner',
         'unique(article_id, partner_id)',
         'You already added this partner on this article.')
    ]

    @api.constrains('article_permission', 'permission')
    def _check_is_writable(self, on_unlink=False):
        """ Articles must always have at least one writer. This constraint is done
        on member level, in coordination to the constraint on article model (see
        ``_check_is_writable`` on ``knowledge.article``).

        Since this constraint only triggers if we have at least one member another
        validation is done on article model. The article_permission related field
        has been added and stored to force triggering this constraint when
        article.permission is modified.

        Ǹote: computation is done in Py instead of using optimized SQL queries
        because value are not yet in DB at this point.

        :param bool on_unlink: when called on unlink we must remove the members
          in self (the ones that will be deleted) to check if one of the remaining
          members has write access.
        """
        if self.env.context.get('knowledge_member_skip_writable_check'):
            return

        articles_to_check = self.article_id.filtered(lambda a: a.inherited_permission != 'write')
        if not articles_to_check:
            return

        if on_unlink:
            deleted_members_by_article = dict.fromkeys(articles_to_check.ids, self.env['knowledge.article.member'])
            for member in self.filtered(lambda member: member.article_id in articles_to_check):
                deleted_members_by_article[member.article_id.id] |= member

        for article in articles_to_check:
            # Check on permission on members
            members_to_check = article.article_member_ids
            if on_unlink:
                members_to_check -= deleted_members_by_article[article.id]
            if any(m.permission == 'write' for m in members_to_check):
                continue

            members_to_exclude = deleted_members_by_article[article.id] if on_unlink else False
            if not article._has_write_member(members_to_exclude=members_to_exclude):
                raise ValidationError(
                    _("Article '%s' should always have a writer: inherit write permission, or have a member with write access",
                      article.display_name)
                )

    def write(self, vals):
        """ Whatever rights, avoid any attempt at privilege escalation. """
        if ('article_id' in vals or 'partner_id' in vals) and not self.env.is_admin():
            raise AccessError(_("Can not update the article or partner of a member."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_no_writer(self):
        """ When removing a member, the constraint is not triggered.
        We need to check manually on article with no write permission that we do not remove the last write member """
        self._check_is_writable(on_unlink=True)

    def _get_invitation_hash(self):
        """ We use a method instead of a field in order to reduce DB space."""
        self.ensure_one()
        return tools.hmac(self.env(su=True),
                          'knowledge-article-invite',
                          f'{self.id}-{self.create_date}-{self.partner_id.id}-{self.article_id.id}'
                         )
