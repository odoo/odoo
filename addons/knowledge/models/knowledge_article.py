# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from werkzeug.urls import url_join
from collections import defaultdict
import sys

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import get_lang, formataddr


class ArticleMembers(models.Model):
    _name = 'knowledge.article.member'
    _description = 'Article Members'
    _table = 'knowledge_article_member_rel'

    article_id = fields.Many2one('knowledge.article', 'Article', ondelete='cascade', required=True)
    partner_id = fields.Many2one('res.partner', index=True, ondelete='cascade', required=True)
    permission = fields.Selection([
        ('none', 'None'),
        ('read', 'Read'),
        ('write', 'Write'),
    ], required=True, default='read')
    article_permission = fields.Selection([
        ('none', 'None'),
        ('read', 'Read'),
        ('write', 'Write'),
    ], string="Article Permission", compute='_compute_article_permission', store=True)
    # used to highlight the current user in the share wizard.
    is_current_user = fields.Boolean(string="Is Me ?", compute="_compute_is_current_user")

    _sql_constraints = [
        ('partner_unique', 'unique(article_id, partner_id)', 'You already added this partner in this article.')
    ]

    @api.constrains('article_permission', 'permission')
    def _check_members(self):
        """
        An article must have at least one member. Since this constrain only triggers if we have at least one member on
        the article, another validation is done in 'knowledge.article' model.
        The article_permission related field has been added and stored to force triggering this constrain when
        article.permission is modified.
        """
        for member in self:
            if member.article_permission != 'write':
                write_members = member.article_id.article_member_ids.filtered(
                        lambda member: member.permission == 'write')
                if len(write_members) == 0:
                    raise ValidationError(_("You must have at least one writer."))

    @api.depends("article_id")
    def _compute_article_permission(self):
        articles_permission = self.article_id._get_internal_permission(article_ids=self.article_id.ids)
        for member in self:
            member.article_permission = articles_permission[member.article_id.id]

    def _compute_is_current_user(self):
        for member in self:
            member.is_current_user = member.partner_id.user_id == self.env.user

    def unlink(self):
        """ When removing a member, the constraint is not triggered.
        We need to check manually on article with no write permission that we do not remove the last write member """
        articles = self.article_id
        members_by_articles = dict.fromkeys(self.article_id.ids, self.env['knowledge.article.member'])
        for member in self:
            members_by_articles[member.article_id.id] |= member
        for article in articles:
            if article.internal_permission == 'write':
                continue
            remaining_members = article.article_member_ids - members_by_articles[article.id]
            if not remaining_members.filtered(lambda m: m.permission == 'write'):
                raise ValidationError(_("You must have at least one writer."))

        return super(ArticleMembers, self).unlink()

class Article(models.Model):
    _name = "knowledge.article"
    _description = "Knowledge Articles"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "favourite_count, create_date desc"

    active = fields.Boolean(default=True)
    name = fields.Char(string="Title", default="New Article")
    body = fields.Html(string="Article Body")
    icon = fields.Char(string='Article Icon', default='fa-file')
    author_ids = fields.Many2many("res.users", string="Authors", default=lambda self: self.env.user)
    is_locked = fields.Boolean(string='Locked', default=False)

    # Hierarchy and sequence
    parent_id = fields.Many2one("knowledge.article", string="Parent Article")
    child_ids = fields.One2many("knowledge.article", "parent_id", string="Child Articles")
    # Set default=0 to avoid false values and messed up sequence order inside same parent
    sequence = fields.Integer(string="Article Sequence", default=0,
                              help="The sequence is computed only among the articles that have the same parent.")
    main_article_id = fields.Many2one('knowledge.article', string="Subject", compute="_compute_main_article_id",
                                        search="_search_main_article_id", recursive=True)

    # Access rules and members + implied category
    internal_permission = fields.Selection([
        ('none', 'None'),
        ('read', 'Read'),
        ('write', 'Write'),
    ], required=False, help="Basic permission for all internal users. External users can still have permissions if they are added to the members.")
    # partner_ids = fields.Many2many("res.partner", string="Article Members", compute="_compute_partner_ids",
    #     inverse="_inverse_partner_ids", search="_search_partner_ids", compute_sudo=True,
    #     help="Article members are the partners that have specific access rules on the related article.")
    article_member_ids = fields.One2many('knowledge.article.member', 'article_id', string='Members Information')
    user_has_access = fields.Boolean(string='Has Access', compute="_compute_user_has_access", search="_search_user_has_access")
    user_can_write = fields.Boolean(string='Can Write', compute="_compute_user_can_write", search="_search_user_can_write")
    category = fields.Selection([
        ('workspace', 'Workspace'),
        ('private', 'Private'),
        ('shared', 'Shared'),
    ], compute="_compute_category", store=True)
    # If Private, who is the owner ?
    owner_id = fields.Many2one("res.users", string="Current Owner", compute="_compute_owner_id", search="_search_owner_id",
                               help="When an article has an owner, it means this article is private for that owner.")

    # Same as write_uid/_date but limited to the body
    last_edition_id = fields.Many2one("res.users", string="Last Edited by")
    last_edition_date = fields.Datetime(string="Last Edited on")

    # Favourite
    is_user_favourite = fields.Boolean(string="Favourite?", compute="_compute_is_user_favourite",
                                       inverse="_inverse_is_user_favourite", search="_search_is_user_favourite")
    favourite_user_ids = fields.Many2many("res.users", "knowledge_favourite_user_rel", "article_id", "user_id",
                                          string="Favourites", copy=False)
    # Set default=0 to avoid false values and messed up order
    favourite_count = fields.Integer(string="#Is Favourite", copy=False, default=0)

    # @api.constrains('internal_permission', 'partner_ids')
    @api.constrains('internal_permission', 'article_member_ids')
    def _check_members(self):
        """ If article has no member, the internal_permission must be write. as article must have at least one writer.
        If article has member, the validation is done in article.member model has we cannot trigger constraint depending
        on fields from related model. see _check_members from 'knowledge.article.member' model for more details. """
        article_permissions = self._get_internal_permission(article_ids=self.ids)
        member_permissions = self._get_article_member_permissions()
        for article in self:
            members = member_permissions.get(article.id)
            if article_permissions[article.id] != 'write' and not any(m['permission'] == 'write' for m in list(members.values())):
                raise ValidationError(_("You must have at least one writer."))

    ##############################
    # Computes, Searches, Inverses
    ##############################

    # @api.depends('article_member_ids.partner_id')
    # def _compute_partner_ids(self):
    #     for article in self:
    #         article.partner_ids = article.article_member_ids.partner_id
    #         print("caca")
    #
    # def _inverse_partner_ids(self):
    #     for article in self:
    #         # pre-save value to avoid having _compute_member_ids interfering
    #         # while building membership status
    #         memberships = article.article_member_ids
    #         partners_current = article.partner_ids
    #         partners_new = partners_current - memberships.partner_id
    #
    #         # add missing memberships - default permission will be read.
    #         self.env['knowledge.article.member'].create([{
    #             'article_id': article.id,
    #             'partner_id': partner.id
    #         } for partner in partners_new])
    #
    # def _search_partner_ids(self, operator, value):
    #     return [('article_member_ids.partner_id', operator, value)]

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_user_has_access(self):
        print("entering user has access")
        if self.env.user.has_group('base.group_system'):
            self.user_has_access = True
            return
        partner_id = self.env.user.partner_id
        if not partner_id:
            self.user_has_access = False
            return
        # get access for current articles from parents
        article_permissions = self._get_internal_permission(article_ids=self.ids)
        member_permissions = self._get_partner_member_permissions(partner_id.id, article_ids=self.ids)
        for article in self:
            if self.env.user.share:
                article.user_has_access = member_permissions.get(article.id, "none") != "none"
            else:
                article.user_has_access = member_permissions[article.id] != "none" if article.id in member_permissions \
                    else article_permissions[article.id] != 'none'

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_user_can_write(self):
        if self.env.user.has_group('base.group_system'):
            self.user_can_write = True
            return

        partner_id = self.env.user.partner_id
        if not partner_id:
            self.user_can_write = False
            return
        # get access for current articles from parents
        article_permissions = self._get_internal_permission(article_ids=self.ids)
        member_permissions = self._get_partner_member_permissions(partner_id.id, article_ids=self.ids)
        for article in self:
            if self.env.user.share:
                article.user_can_write = member_permissions.get(article.id) == "write"
            else:
                # You cannot have only one member per article.
                article.user_can_write = member_permissions[article.id] == "write" if article.id in member_permissions \
                    else article_permissions[article.id] == 'write'

    @api.depends('internal_permission', 'article_member_ids.permission', 'article_member_ids.partner_id')
    def _compute_category(self):
        for article in self:
            if article.main_article_id.internal_permission != 'none':
                article.category = 'workspace'
            elif len(article.main_article_id.article_member_ids) > 1:
                article.category = 'shared'
            elif len(article.main_article_id.article_member_ids) == 1 and article.main_article_id.article_member_ids.permission == 'write':
                article.category = 'private'
            else:  # should never happen. If an article has no category, there is an error in it's access rules.
                article.category = False

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_owner_id(self):
        article_permissions = self._get_internal_permission(article_ids=self.ids)
        member_permissions = self._get_article_member_permissions()
        Partner = self.env['res.partner']
        for article in self:
            members = member_permissions.get(article.id)
            partner = Partner.browse(list(members.keys())[0]) if len(members) == 1 else False
            if article_permissions[article.id] != 'none':
                article.owner_id = False
            elif partner and list(members.values())[0]['permission'] == 'write' and not partner.partner_share and partner.user_ids:
                article.owner_id = next(user for user in partner.user_ids if not user.share)
            else:
                article.owner_id = False

    @api.depends('parent_id')
    def _compute_main_article_id(self):
        for article in self:
            article.main_article_id = article._get_highest_parent()

    def _search_user_has_access(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError("unsupported search operator")

        article_permissions = self._get_internal_permission(check_access=True)

        member_permissions = self._get_partner_member_permissions(self.env.user.partner_id.id)
        articles_with_no_access = [id for id, permission in member_permissions.items() if permission == 'none']
        articles_with_access = [id for id, permission in member_permissions.items() if permission != 'none']

        # If searching articles for which user has access.
        if (value and operator == '=') or (not value and operator == '!='):
            if self.env.user.has_group('base.group_system'):
                return expression.TRUE_DOMAIN
            elif self.env.user.share:
                return [('id', 'in', articles_with_access)]
            return ['|', '&', ('id', 'in', list(article_permissions.keys())), ('id', 'not in', articles_with_no_access),
                         ('id', 'in', articles_with_access)]
        # If searching articles for which user has NO access.
        if self.env.user.has_group('base.group_system'):
            return expression.FALSE_DOMAIN
        elif self.env.user.share:
            return [('id', 'not in', articles_with_access)]
        return ['|', '&', ('id', 'not in', list(article_permissions.keys())), ('id', 'not in', articles_with_access),
                     ('id', 'in', articles_with_no_access)]

    def _search_user_can_write(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError("unsupported search operator")

        article_permissions = self._get_internal_permission(check_write=True)

        member_permissions = self._get_partner_member_permissions(self.env.user.partner_id.id)
        articles_with_no_access = [id for id, permission in member_permissions.items() if permission != 'write']
        articles_with_access = [id for id, permission in member_permissions.items() if permission == 'write']

        # If searching articles for which user has write access.
        if self.env.user.has_group('base.group_system'):
            return expression.TRUE_DOMAIN
        elif self.env.user.share:
            return [('id', 'in', articles_with_access)]
        if (value and operator == '=') or (not value and operator == '!='):
            return ['|', '&', ('id', 'in', list(article_permissions.keys())), ('id', 'not in', articles_with_no_access),
                         ('id', 'in', articles_with_access)]
        # If searching articles for which user has NO write access.
        if self.env.user.has_group('base.group_system'):
            return expression.FALSE_DOMAIN
        elif self.env.user.share:
            return [('id', 'not in', articles_with_access)]
        return ['|', '&', ('id', 'not in', list(article_permissions.keys())), ('id', 'not in', articles_with_access),
                     ('id', 'in', articles_with_no_access)]

    def _search_owner_id(self, operator, value):
        # get the user_id from name
        if isinstance(value, str):
            value = self.env['res.users'].search([('name', operator, value)]).ids
            if not value:
                return expression.FALSE_DOMAIN
            operator = '='  # now we will search for articles that match the retrieved users.
        # Assumes operator is '=' and value is a user_id or False
        elif operator not in ('=', '!='):
            raise NotImplementedError()

        # if value = False and operator = '!=' -> We look for all the private articles.
        domain = [('category', '=' if value or operator == '!=' else '!=', 'private')]
        if value:
            if isinstance(value, int):
                value = [value]
            users_partners = self.env['res.users'].browse(value).mapped('partner_id')
            article_members = self._get_article_member_permissions()
            def filter_on_permission(members, permission):
                for partner_id, member_info in members.items():
                    if member_info['permission'] == permission:
                        yield partner_id

            import logging
            _logger = logging.getLogger(__name__)
            start = datetime.now()
            articles_with_access = [article_id
                                    for article_id, members in article_members.items()
                                    if any(partner_id in filter_on_permission(members, "write")
                                           for partner_id in users_partners.ids)]
            domain = expression.AND([domain, [('id', 'in' if operator == '=' else 'not in', articles_with_access)]])
        return domain

    def _compute_is_user_favourite(self):
        for article in self:
            article.is_user_favourite = self.env.user in article.favourite_user_ids

    def _inverse_is_user_favourite(self):
        favorite_articles = not_fav_articles = self.env['knowledge.article']
        for article in self:
            if self.env.user in article.favourite_user_ids:  # unset as favourite
                not_fav_articles |= article
            else:  # set as favourite
                favorite_articles |= article

        favorite_articles.write({'favourite_user_ids': [(4, self.env.uid)]})
        not_fav_articles.write({'favourite_user_ids': [(3, self.env.uid)]})

        for article in not_fav_articles:
            article.favourite_count -= 1
        for article in favorite_articles:
            article.favourite_count += 1

    def _search_is_user_favourite(self, operator, value):
        if operator != "=":
            raise NotImplementedError("Unsupported search operation on favourite articles")

        if value:
            return [('favourite_user_ids', 'in', [self.env.user.id])]
        else:
            return [('favourite_user_ids', 'not in', [self.env.user.id])]

    def _search_main_article_id(self, operator, value):
        if isinstance(value, str):
            value = self.search([('name', operator, value)]).ids
            if not value:
                return expression.FALSE_DOMAIN
            operator = '='  # now we will search for articles that match the retrieved users.
        elif operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError()
        articles = self
        search_operator = 'in' if operator in ('=', 'in') else 'not in'
        for article in self.search([('id', search_operator, value)]):
            articles |= article._get_descendants()
            articles |= article
        return [('id', 'in', articles.ids)]

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ Override to support ordering on is_user_favourite.

        Ordering through web client calls search_read with an order parameter set.
        Search_read then calls search. In this override we therefore override search
        to intercept a search without count with an order on is_user_favourite.
        In that case we do the search in two steps.

        First step: fill with current user's favourite results

          * Search articles that are favourite of the current user.
          * Results of that search will be at the top of returned results. Use limit
            None because we have to search all favourite articles.
          * Finally take only a subset of those articles to fill with
            results matching asked offset / limit.

        Second step: fill with other results. If first step does not gives results
        enough to match offset and limit parameters we fill with a search on other
        articles. We keep the asked domain and ordering while filtering out already
        scanned articles to keep a coherent results.

        All other search and search_read are left untouched by this override to avoid
        side effects. Search_count is not affected by this override.
        """
        if count or not order or 'is_user_favourite' not in order:
            return super(Article, self).search(args, offset=offset, limit=limit, order=order, count=count)
        order_items = [order_item.strip().lower() for order_item in (order or self._order).split(',')]
        favourite_asc = any('is_user_favourite asc' in item for item in order_items)

        # Search articles that are favourite of the current user.
        my_articles_domain = expression.AND([[('favourite_user_ids', 'in', [self.env.user.id])], args])
        my_articles_order = ', '.join(item for item in order_items if 'is_user_favourite' not in item)
        articles_ids = super(Article, self).search(my_articles_domain, offset=0, limit=None, order=my_articles_order, count=count).ids

        # keep only requested window (offset + limit, or offset+)
        my_articles_ids_keep = articles_ids[offset:(offset + limit)] if limit else articles_ids[offset:]
        # keep list of already skipped article ids to exclude them from future search
        my_articles_ids_skip = articles_ids[:(offset + limit)] if limit else articles_ids

        # do not go further if limit is achieved
        if limit and len(my_articles_ids_keep) >= limit:
            return self.browse(my_articles_ids_keep)

        # Fill with remaining articles. If a limit is given, simply remove count of
        # already fetched. Otherwise keep none. If an offset is set we have to
        # reduce it by already fetch results hereabove. Order is updated to exclude
        # is_user_favourite when calling super() .
        article_limit = (limit - len(my_articles_ids_keep)) if limit else None
        if offset:
            article_offset = max((offset - len(articles_ids), 0))
        else:
            article_offset = 0
        article_order = ', '.join(item for item in order_items if 'is_user_favourite' not in item)

        other_article_res = super(Article, self).search(
            expression.AND([[('id', 'not in', my_articles_ids_skip)], args]),
            offset=article_offset, limit=article_limit, order=article_order, count=count
        )
        if favourite_asc in order_items:
            return other_article_res + self.browse(my_articles_ids_keep)
        else:
            return self.browse(my_articles_ids_keep) + other_article_res

    ##########
    #  CRUD  #
    ##########

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['last_edition_id'] = self._uid
            vals['last_edition_date'] = fields.Datetime.now()

        articles = super(Article, self).create(vals_list)
        for article, vals in zip(articles, vals_list):
            if any(field in ['parent_id', 'sequence'] for field in vals) and not self.env.context.get('resequencing_articles'):
                article.with_context(resequencing_articles=True)._resequence()
        return articles

    def write(self, vals):
        """ Add editor as author. Edition means writing on the body. """
        if 'body' in vals:
            vals.update({
                "author_ids": [(4, self._uid)],  # add editor as author.
                "last_edition_id": self._uid,
                "last_edition_date": fields.Datetime.now(),
            })

        result = super(Article, self).write(vals)

        # use context key to stop reordering loop as "_resequence" calls write method.
        if any(field in ['parent_id', 'sequence'] for field in vals) and not self.env.context.get('resequencing_articles'):
            self.with_context(resequencing_articles=True)._resequence()

        return result

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {},
                       name=_("%s (copy)", self.name),
                       sequence=self.sequence+1)
        return super().copy(default=default)

    def unlink(self):
        for article in self:
            # Make all the article's children be adopted by the parent's parent.
            # Otherwise, we will have to manage an orphan house.
            parent = article.parent_id
            if parent:
                article.child_ids.write({"parent_id": parent.id})
        return super(Article, self).unlink()

    #########
    # Actions
    #########

    def action_home_page(self):
        action = self.env['ir.actions.act_window']._for_xml_id('knowledge.knowledge_article_dashboard_action')
        action['res_id'] = self.env.context.get('res_id', self.search([('parent_id', '=', False), ('internal_permission', '!=', 'none')], limit=1, order='sequence').id)
        return action

    def action_set_lock(self):
        for article in self:
            article.is_locked = True

    def action_set_unlock(self):
        for article in self:
            article.is_locked = False

    def action_archive(self):
        return super(Article, self | self._get_descendants()).action_archive()

    #####################
    #  Business methods
    #####################

    def move_to(self, parent_id=False, before_article_id=False, private=False):
        self.ensure_one()
        if not self.user_can_write:
            raise AccessError(_('You are not allowed to move this article.'))
        parent = self.browse(parent_id) if parent_id else False
        if parent and not parent.user_can_write:
            raise AccessError(_('You are not allowed to move this article under this parent.'))
        before_article = self.browse(before_article_id) if before_article_id else False

        # as base user doesn't have access to members, use sudo to allow access it.
        article_sudo = self.sudo()

        if before_article:
            sequence = before_article.sequence
        else:
            # get max sequence among articles with the same parent
            sequence = article_sudo._get_max_sequence_inside_parent(parent_id)

        values = {
            'parent_id': parent_id,
            'sequence': sequence
        }
        if not parent_id:
            # If parent_id, the write method will set the internal_permission based on the parent.
            # If moved from workspace to private -> set none. If moved from private to workspace -> set write
            values['internal_permission'] = 'none' if private else 'write'

        members_to_remove = self.env['knowledge.article.member']
        if not parent and private:  # If set private without parent, remove all members except current user.
            member = article_sudo.article_member_ids.filtered(lambda m: m.partner_id == self.env.user.partner_id)
            if member:
                members_to_remove = article_sudo.article_member_ids.filtered(lambda m: m.id != member.id)
                values.update({
                    'article_member_ids': [(1, member.id, {
                        'permission': 'write'
                    })]
                })
            else:
                members_to_remove = article_sudo.article_member_ids
                values.update({
                    'article_member_ids': [(0, 0, {
                        'partner_id': self.env.user.partner_id.id,
                        'permission': 'write'
                    })]
                })

        article_sudo.sudo().write(values)
        members_to_remove.unlink()

        return True

    def article_create(self, title=False, parent_id=False, private=False):
        parent = self.browse(parent_id) if parent_id else False

        if parent:
            if private and parent.category != "private":
                raise ValidationError(_("Cannot create an article under a non-private parent"))
            if not private and parent.category == "private":
                raise ValidationError(_("Cannot create a non-private article under a private parent"))
            if not parent.user_can_write:
                raise AccessError(_("Cannot create an article under a parent article you can't write on"))
            if private and not parent.owner_id == self.env.user:
                raise AccessError(_("Cannot create an article under a non-owned private article"))
        values = {
            'parent_id': parent_id,
            'sequence': self._get_max_sequence_inside_parent(parent_id)
        }
        if not parent:
            values.update({
                'internal_permission': 'none' if private else 'write', # you cannot create an article without parent in shared directly.,
            })
        # User cannot write on members, sudo is needed to allow to create a private article or create under a parent user can write on.
        # for article without parent or not in private, access to members is not required to create an article
        if (private or parent) and self.env.user.has_group('base.group_user'):
            self = self.sudo()
        if not parent and private:
            # To be private, the article hierarchy need at least one member with write access.
            values.update({
                'article_member_ids': [(0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                })]
            })

        if title:
            values.update({
                'name': title,
                'body': title
            })

        article = self.create(values)

        return article.id

    # Permission and members handling methods
    # ---------------------------------------

    def set_article_permission(self, permission):
        self.ensure_one()
        if self.user_can_write:
            self.write({'internal_permission': permission})

    def set_member_permission(self, partner_id, permission):
        self.ensure_one()
        if self.user_can_write:
            member = self.sudo().article_member_ids.filtered(lambda member: member.partner_id.id == partner_id)
            member.write({'permission': permission})

    # def remove_member(self, partner_id):
    #     self.ensure_one()
    #     if self.user_can_write:
    #         member = self.main_article_id.sudo().article_member_ids.filtered(lambda member: member.partner_id.id == partner_id)
    #         member.unlink()

    def invite_member(self, access_rule, partner_id=False, email=False, send_mail=True):
        self.ensure_one()
        if self.user_can_write:
            # A priori no reason to give a wrong partner_id at this stage as user must be logged in and have access.
            partner = self.env['res.partner'].browse(partner_id)
            self.sudo()._invite_member(access_rule, partner=partner, email=email, send_mail=send_mail)
        else:
            raise UserError(_("You cannot give access to this article as you are not editor."))

    def _invite_member(self, access_rule, partner=False, email=False, send_mail=True):
        self.ensure_one()
        if not email and not partner:
            raise UserError(_('You need to provide an email address or a partner to invite a member.'))
        if email and not partner:
            try:
                partner = self.env["res.partner"].find_or_create(email, assert_valid_email=True)
            except ValueError:
                raise ValueError(_('The given email address is incorrect.'))

        # add member
        member = self.sudo().article_member_ids.filtered(lambda member: member.partner_id == partner)
        if member:
            member.write({'permission': access_rule})
        else:
            self.write({
                'article_member_ids': [(0, 0, {
                    'partner_id': partner.id,
                    'permission': access_rule
                })]
        })
        if not member and send_mail:
            self._send_invite_mail(partner)

    def _send_invite_mail(self, partner):
        self.ensure_one()
        subject = _("Invitation to access %s", self.name)
        partner_lang = get_lang(self.env, lang_code=partner.lang).code
        tpl = self.env.ref('knowledge.knowledge_article_mail_invite')
        body = tpl.with_context(lang=partner_lang)._render({
            'record': self,
            'user': self.env.user,
            'recipient': partner,
            'link': self._get_invite_url(partner),
        }, engine='ir.qweb', minimal_qcontext=True)

        self._send_mail(
            body, {'record_name': self.name},
            {'model_description': 'Article', 'company': self.create_uid.company_id},
            {'email_from': self.env.user.email_formatted,
             'author_id': self.env.user.partner_id.id,
             'email_to': formataddr((partner.name, partner.email_formatted)),
             'subject': subject},
            partner_lang)

    def _send_mail(self, body, message_values, notif_values, mail_values, partner_lang):
        article = self.with_context(lang=partner_lang)
        msg = article.env['mail.message'].sudo().new(dict(body=body, **message_values))
        email_layout = article.env.ref('mail.mail_notification_light')
        body_html = email_layout._render(dict(message=msg, **notif_values), engine='ir.qweb', minimal_qcontext=True)
        body_html = article.env['mail.render.mixin']._replace_local_links(body_html)

        mail = article.env['mail.mail'].sudo().create(dict(body_html=body_html, **mail_values))
        mail.send()

    def _get_invite_url(self, partner):
        self.ensure_one()
        return url_join(self.get_base_url(), "/article/%s/invite/%s" % (self.id, partner.id))

    # TODO: remove me - for test purpose only
    def invite_test(self):
        self.invite_member(access_rule='read', partner_id=self.env.ref('base.partner_demo_portal').id)

    ###########
    #  Tools
    ###########

    def _get_internal_permission(self, article_ids=False, check_access=False, check_write=False):
        """ We don't use domain because we cannot include properly the where clause in the custom sql query.
        The query's output table and fields names does not match the model we are working on"""
        domain = []
        args = []
        if article_ids:
            args = [tuple(article_ids)]
            domain.append("original_id in %s")
        if check_access:
            domain.append("internal_permission != 'none'")
        elif check_write:
            domain.append("internal_permission = 'write'")
        domain = ("WHERE " + " AND ".join(domain)) if domain else ''

        sql = '''WITH RECURSIVE acl as (
                    SELECT id, id as original_id, parent_id, internal_permission
                        FROM knowledge_article
                    UNION 
                    SELECT t.id, p.original_id, t.parent_id, COALESCE(p.internal_permission, t.internal_permission)
                        FROM knowledge_article t INNER JOIN acl p 
                        ON (p.parent_id=t.id and p.internal_permission is null)) 
                 SELECT original_id, max(internal_permission)
                    FROM acl 
                    %s
                    GROUP BY original_id''' % domain
        self._cr.execute(sql, args)
        return dict(self._cr.fetchall())

    def _get_partner_member_permissions(self, partner_id, article_ids=False):
        """ Retrieve the permission for the given partner for all articles.
        The articles can be filtered using the article_ids param."""
        domain = "WHERE permission is not null"
        args = []
        if article_ids:
            args = [tuple(article_ids)]
            domain += " AND original_id in %s"

        sql = '''WITH RECURSIVE
                    perm as (SELECT a.id, a.parent_id, m.permission
                        FROM knowledge_article a LEFT JOIN knowledge_article_member_rel m
                        ON a.id=m.article_id and partner_id = %s),
                    rec as (
                        SELECT t.id, t.id as original_id, t.parent_id, t.permission
                            FROM perm as t
                        UNION 
                        SELECT t1.id, p.original_id, t1.parent_id, COALESCE(p.permission, t1.permission)
                            FROM perm as t1 
                            INNER JOIN rec p 
                            ON (p.parent_id=t1.id and p.permission is null)) 
                 SELECT original_id, max(permission)
                    FROM rec
                    %s 
                    GROUP BY original_id''' % (partner_id, domain)

        self._cr.execute(sql, args)
        return dict(self._cr.fetchall())

    def _get_article_member_permissions(self):
        """ Retrieve the permission for all the members that apply to the target article.
        Members that apply are not only the ones on the article but can also come from parent articles."""
        domain = "WHERE partner_id is not null"
        args = []
        if self.ids:
            args = [tuple(self.ids)]
            domain += " AND original_id in %s"
        sql = '''WITH RECURSIVE 
                    perm as (SELECT a.id, a.parent_id, m.partner_id, m.permission
                                    FROM knowledge_article a
                                    LEFT JOIN knowledge_article_member_rel m ON a.id = m.article_id),
                    rec as (
                        SELECT t.id, t.id as original_id, t.parent_id, t.partner_id, t.permission, t.id as origin, 0 as level
                            FROM perm as t
                        UNION 
                        SELECT t1.id, p.original_id, t1.parent_id, t1.partner_id, t1.permission, t1.id as origin, p.level + 1
                            FROM perm as t1 
                            INNER JOIN rec p 
                            ON (p.parent_id=t1.id)) 
                SELECT original_id, origin, partner_id, permission, min(level)
                        FROM rec
                        %s GROUP BY original_id, origin, partner_id, permission''' % domain

        self._cr.execute(sql, args)
        results = self._cr.fetchall()
        # Now that we have, for each article, all the members found on themselves and their parents.
        # We need to keep only the first partners found (lowest level) for each article
        article_members = defaultdict(dict)
        min_level_dict = defaultdict(dict)
        for result in results:
            [article_id, origin_id, partner_id, permission, level] = result
            min_level = min_level_dict[article_id].get(partner_id, sys.maxsize)
            if level < min_level:
                article_members[article_id][partner_id] = {'based_on': origin_id if origin_id != article_id else False, 'permission': permission}
                min_level_dict[article_id][partner_id] = level
        # add empty member for each article that doesn't have any.
        for article in self:
            if article.id not in article_members:
                article_members[article.id][None] = {'based_on': False, 'permission': None}

        return article_members

    def _get_max_sequence_inside_parent(self, parent_id):
        # TODO DBE: maybe order the childs_ids in desc on parent should be enough
        max_sequence_article = self.search(
            [('parent_id', '=', parent_id)],
            order="sequence desc",
            limit=1
        )
        return max_sequence_article.sequence + 1 if max_sequence_article else 0

    def _get_highest_parent(self):
        self.ensure_one()
        if self.parent_id:
            return self.parent_id._get_highest_parent()
        else:
            return self

    def _get_descendants(self):
        """ Returns the descendants recordset of the current article. """
        descendants = self.env['knowledge.article']
        for child in self.child_ids:
            descendants |= child
            descendants |= child._get_descendants()
        return descendants

    def _resequence(self):
        """ This method re-order the children of the same parent (brotherhood) if needed.
         If an article have been moved from one parent to another, we don't need to resequence the children of the
         old parent as the order remains unchanged. We only need to resequence the children of the new parent only if
         the sequences of the children contains duplicates. When reordering an article, we assume that we always set
         the sequence equals to the position we want it to be, and we use the write_date to differentiate the new order
         between duplicates in sequence.
         So if we want article D to be placed at 3rd position between A B et C: set D.sequence = 2, but C was already 2.
         To know which one is the real 3rd in position, we use the write_date. The last modified is the real 3rd. """
        write_vals_by_sequence = {}
        # Resequence articles with parents
        parents = self.mapped("parent_id")
        for parent in parents:
            children = self.search([("parent_id", '=', parent.id)], order="sequence,write_date desc")
            self._resequence_children(children, write_vals_by_sequence)
        # Resequence articles with no parent
        if any(not article.parent_id for article in self):
            children = self.search([("parent_id", '=', False)], order="sequence,write_date desc")
            self._resequence_children(children, write_vals_by_sequence)

        for sequence in write_vals_by_sequence:
            write_vals_by_sequence[sequence].write({'sequence': sequence})

    def _resequence_children(self, children, write_vals_by_sequence):
        children_sequences = children.mapped('sequence')
        # no need to resequence if no duplicates.
        if len(children_sequences) == len(set(children_sequences)):
            return

        # find index of duplicates
        duplicate_index = [idx for idx, item in enumerate(children_sequences) if item in children_sequences[:idx]][0]
        start_sequence = children_sequences[duplicate_index] + 1
        # only need to resequence after the duplicate: allow holes in the sequence but limit number of write operations.
        children = children[duplicate_index:]
        for i, child in enumerate(children):
            if i + start_sequence not in write_vals_by_sequence:
                write_vals_by_sequence[i + start_sequence] = child
            else:
                write_vals_by_sequence[i + start_sequence] |= child
