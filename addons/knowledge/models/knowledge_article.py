# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from collections import defaultdict
from markupsafe import Markup
from werkzeug.urls import url_join

from odoo import Command, fields, models, api, _
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import get_lang

ARTICLE_PERMISSION_LEVEL = {'none': 0, 'read': 1, 'write': 2}


class Article(models.Model):
    _name = "knowledge.article"
    _description = "Knowledge Article"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "favorite_count, create_date desc, id desc"
    _mail_post_access = 'read'

    active = fields.Boolean(default=True)
    name = fields.Char(string="Title", default=lambda self: _('New Article'), required=True, tracking=20)
    body = fields.Html(string="Body")
    icon = fields.Char(string='Emoji')
    cover = fields.Binary(string='Cover Image')
    is_locked = fields.Boolean(
        string='Locked',
        help="When locked, users cannot write on the body or change the title, "
             "even if they have write access on the article.")
    full_width = fields.Boolean(
        string='Full width',
        help="When set, the article body will take the full width available on the article page. "
             "Otherwise, the body will have large horizontal margins.")
    article_url = fields.Char('Article URL', compute='_compute_article_url', readonly=True)
    # Hierarchy and sequence
    parent_id = fields.Many2one("knowledge.article", string="Parent Article", tracking=30)
    child_ids = fields.One2many("knowledge.article", "parent_id", string="Child Articles")
    is_desynchronized = fields.Boolean(
        string="Desyncronized with parents",
        help="If set, this article won't inherit access rules from its parents anymore.")
    sequence = fields.Integer(
        string="Sequence",
        default=0,  # Set default=0 to avoid false values and messed up sequence order inside same parent
        help="The sequence is computed only among the articles that have the same parent.")
    root_article_id = fields.Many2one(
        'knowledge.article', string="Subject", recursive=True,
        compute="_compute_root_article_id", store=True, compute_sudo=True, tracking=10,
        help="The subject is the title of the highest parent in the article hierarchy.")
    # Access rules and members + implied category
    internal_permission = fields.Selection(
        [('write', 'Can write'), ('read', 'Can read'), ('none', 'No access')],
        string='Internal Permission', required=False,
        help="Default permission for all internal users. "
             "(External users can still have access to this article if they are added to its members)")
    inherited_permission = fields.Selection(
        [('write', 'Can write'), ('read', 'Can read'), ('none', 'No access')],
        string='Inherited Permission',
        compute="_compute_inherited_permission", compute_sudo=True,
        store=True, recursive=True)
    inherited_permission_parent_id = fields.Many2one(
        "knowledge.article", string="Inherited Permission Parent Article",
        compute="_compute_inherited_permission", compute_sudo=True,
        store=True, recursive=True)
    article_member_ids = fields.One2many(
        'knowledge.article.member', 'article_id', string='Members Information',
        copy=True)
    user_has_access = fields.Boolean(
        string='Has Access',
        compute="_compute_user_has_access", search="_search_user_has_access")
    user_has_write_access = fields.Boolean(
        string='Can Write',
        compute="_compute_user_has_write_access", search="_search_user_has_write_access")
    user_permission = fields.Selection(
        [('write', 'write'), ('read', 'read'), ('none', 'none')],
        string='User permission',
        compute='_compute_user_permission')
    # categories and ownership
    category = fields.Selection(
        [('workspace', 'Workspace'), ('private', 'Private'), ('shared', 'Shared')],
        compute="_compute_category", compute_sudo=True, store=True,
        help='Used to categozie articles in UI, depending on their main permission definitions.')
        # Stored to improve performance when loading the article tree. (avoid looping through members if 'workspace')
    # Same as write_uid/_date but limited to the body
    last_edition_uid = fields.Many2one(
        "res.users", string="Last Edited by",
        compute='_compute_last_edition_data', store=True,
        readonly=False, copy=False)
    last_edition_date = fields.Datetime(
        string="Last Edited on",
        compute='_compute_last_edition_data', store=True,
        readonly=False, copy=False)
    # Favorite
    is_user_favorite = fields.Boolean(
        string="Is Favorited",
        compute="_compute_is_user_favorite",
        inverse="_inverse_is_user_favorite",
        search="_search_is_user_favorite")
    user_favorite_sequence = fields.Integer(string="User Favorite Sequence", compute="_compute_is_user_favorite")
    favorite_ids = fields.One2many(
        'knowledge.article.favorite', 'article_id',
        string='Favorite Articles', copy=False)
    # Set default=0 to avoid false values and messed up order
    favorite_count = fields.Integer(
        string="#Is Favorite",
        compute="_compute_favorite_count", store=True, copy=False, default=0)

    _sql_constraints = [
        ('check_permission_on_root',
         'check(parent_id IS NOT NULL OR internal_permission IS NOT NULL)',
         'Root articles must have internal permission.'
        ),
        ('check_permission_on_desync',
         'check(is_desynchronized IS NOT TRUE OR internal_permission IS NOT NULL)',
         'Desynchronized articles must have internal permission.'
        ),
        ('check_desync_on_root',
         'check(parent_id IS NOT NULL OR is_desynchronized IS NOT TRUE)',
         'Root articles cannot be desynchronized.'
        ),
    ]

    # ------------------------------------------------------------
    # CONSTRAINTS
    # ------------------------------------------------------------

    @api.constrains('internal_permission', 'article_member_ids')
    def _check_is_writable(self):
        """ Articles must always have at least one writer. This constraint is done
        on article level, in coordination to the constraint on member model (see
        ``_check_is_writable`` on ``knowledge.article.member``).

        If article has no member the internal_permission must be write. If article
        has members validation is done in article.member model as we cannot trigger
        the constraint depending on fields from related model.

        Ǹote: computation is done in Py instead of using optimized SQL queries
        because value are not yet in DB at this point."""
        for article in self:
            def has_write_member(a, child_members=False):
                if not child_members:
                    child_members = self.env['knowledge.article.member']
                article_members = a.article_member_ids
                if any(m.permission == 'write' and m.partner_id not in child_members.mapped('partner_id')
                       for m in article_members):
                    return True
                if a.parent_id and not a.is_desynchronized:
                    return has_write_member(a.parent_id, article_members | child_members)
                return False
            if article.inherited_permission != 'write' and not has_write_member(article):
                raise ValidationError(_("The article '%s' needs at least one member with 'Write' access.", article.display_name))

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise ValidationError(
                _('Articles %s cannot be updated as this would create a recursive hierarchy.',
                  ', '.join(self.mapped('name'))
                 )
            )

    def name_get(self):
        return [(rec.id, "%s %s" % (rec.icon or "📄", rec.name)) for rec in self]

    # ------------------------------------------------------------
    # COMPUTED FIELDS
    # ------------------------------------------------------------

    def _compute_article_url(self):
        for article in self:
            if not article.ids:
                article.article_url = False
            else:
                article.article_url = url_join(article.get_base_url(), 'knowledge/article/%s' % article.id)

    @api.depends('parent_id', 'parent_id.root_article_id')
    def _compute_root_article_id(self):
        wparent = self.filtered('parent_id')
        for article in self - wparent:
            article.root_article_id = article

        if not wparent:
            return
        # group by parents to lessen number of computation
        articles_byparent = defaultdict(lambda: self.env['knowledge.article'])
        for article in wparent:
            articles_byparent[article.parent_id] += article

        for parent, articles in articles_byparent.items():
            ancestors = self.env['knowledge.article']
            while parent:
                if parent in ancestors:
                    raise ValidationError(
                        _('Articles %s cannot be updated as this would create a recursive hierarchy.',
                          ', '.join(articles.mapped('name'))
                         )
                    )
                ancestors += parent
                parent = parent.parent_id
            articles.root_article_id = ancestors[-1:]

    @api.depends('parent_id', 'internal_permission')
    def _compute_inherited_permission(self):
        """ Computed inherited internal permission. We go up ancestors until
        finding an article with an internal permission set, or a root article
        (without parent) or until finding a desynchronized article which
        serves as permission ancestor. Desynchronized articles break the
        permission tree finding. """
        self_inherit = self.filtered(lambda article: article.internal_permission)
        for article in self_inherit:
            article.inherited_permission = article.internal_permission
            article.inherited_permission_parent_id = False

        remaining = self - self_inherit
        if not remaining:
            return
        # group by parents to lessen number of computation
        articles_byparent = defaultdict(lambda: self.env['knowledge.article'])
        for article in remaining:
            articles_byparent[article.parent_id] += article

        for parent, articles in articles_byparent.items():
            ancestors = self.env['knowledge.article']
            while parent:
                if parent in ancestors:
                    raise ValidationError(
                        _('Articles %s cannot be updated as this would create a recursive hierarchy.',
                          ', '.join(articles.mapped('name'))
                         )
                    )
                ancestors += parent
                if parent.internal_permission or parent.is_desynchronized:
                    break
                parent = parent.parent_id
            articles.inherited_permission = ancestors[-1:].internal_permission
            articles.inherited_permission_parent_id = ancestors[-1:]

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_user_permission(self):
        """ Compute permission for current user. Public users never have any
        permission. Shared users have permission based only on members permission
        as internal permission never apply to them. Internal users combine both
        internal and members permissions, taking the highest one. """
        if self.env.user._is_public():
            self.user_permission = False
            return

        # split transient due to direct SQL query to perform
        transient = self.filtered(lambda article: not article.ids)
        transient.user_permission = 'write'  # not created yet, set default permission value
        toupdate = self - transient
        if not toupdate:
            return

        articles_permissions = {}
        if not self.env.user.share:
            articles_permissions = self._get_internal_permission()
        member_permissions = self._get_partner_member_permissions(self.env.user.partner_id)
        for article in self:
            article_id = article.ids[0]
            if self.env.user.share:
                article.user_permission = member_permissions.get(article_id, False)
            else:
                article.user_permission = member_permissions.get(article_id, False) \
                                          or articles_permissions[article_id]

    @api.depends_context('uid')
    @api.depends('user_permission')
    def _compute_user_has_access(self):
        """ Compute if the current user has read access to the article based on
        permissions and memberships.

        Note that admins have all access through ACLs by default but fields are
        still using the permission-based computation. """
        for article in self:
            article.user_has_access = article.user_permission != 'none' if article.user_permission else False

    def _search_user_has_access(self, operator, value):
        """ This search method looks at article and members permissions to return
        all the article the current user has access to.

        Heuristic is
        - External users only have access to an article if they are r/w member
          on that article;
        - Internal users have access if:
          - they are read or write member on the article
          OR
          - The article allow read or write access to all internal users AND the user
            is not member with 'none' access
        """
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError("Unsupported search operator")

        articles_with_access = {}
        if not self.env.user.share:
            articles_with_access = self._get_internal_permission(filter_domain=[('internal_permission', '!=', 'none')])
        member_permissions = self._get_partner_member_permissions(self.env.user.partner_id)
        articles_with_no_member_access = [article_id for article_id, perm in member_permissions.items() if perm == 'none']
        articles_with_member_access = list(set(member_permissions.keys() - set(articles_with_no_member_access)))

        # If searching articles for which user has access.
        if (value and operator == '=') or (not value and operator == '!='):
            if self.env.user.share:
                return [('id', 'in', articles_with_member_access)]
            return ['|',
                    '&', ('id', 'in', list(articles_with_access.keys())), ('id', 'not in', articles_with_no_member_access),
                    ('id', 'in', articles_with_member_access)]

        # If searching articles for which user has NO access.
        if self.env.user.share:
            return [('id', 'not in', articles_with_member_access)]
        return ['|',
                '&', ('id', 'not in', list(articles_with_access.keys())), ('id', 'not in', articles_with_member_access),
                ('id', 'in', articles_with_no_member_access)]

    @api.depends_context('uid')
    @api.depends('user_permission')
    def _compute_user_has_write_access(self):
        """ Compute if the current user has read access to the article based on
        permissions and memberships.

        Note that share user can never write and we therefore shorten the computation.

        Note that admins have all access through ACLs by default but fields are
        still using the permission-based computation. """
        if self.env.user.share:
            self.user_has_write_access = False
            return
        for article in self:
            article.user_has_write_access = article.user_permission == 'write'

    def _search_user_has_write_access(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError("Unsupported search operator")

        # share is never allowed to write
        if self.env.user.share:
            if (value and operator == '=') or (not value and operator == '!='):
                return expression.FALSE_DOMAIN
            return expression.TRUE_DOMAIN

        articles_with_access = self._get_internal_permission(filter_domain=[('internal_permission', '=', 'write')])
        member_permissions = self._get_partner_member_permissions(self.env.user.partner_id)
        articles_with_member_access = [article_id for article_id, perm in member_permissions.items() if perm == 'write']
        articles_with_no_member_access = list(set(member_permissions.keys() - set(articles_with_member_access)))

        # If searching articles for which user has write access.
        if (value and operator == '=') or (not value and operator == '!='):
            return ['|',
                        '&', ('id', 'in', list(articles_with_access.keys())), ('id', 'not in', articles_with_no_member_access),
                        ('id', 'in', articles_with_member_access)
            ]
        # If searching articles for which user has NO write access.
        return ['|',
                    '&', ('id', 'not in', list(articles_with_access.keys())), ('id', 'not in', articles_with_member_access),
                    ('id', 'in', articles_with_no_member_access)
        ]

    @api.depends('root_article_id.internal_permission', 'root_article_id.article_member_ids.permission')
    def _compute_category(self):
        # compute workspace articles
        workspace_articles = self.filtered(lambda a: a.root_article_id.internal_permission != 'none')
        workspace_articles.category = 'workspace'

        remaining_articles = self - workspace_articles
        if not remaining_articles:
            return

        results = self.env['knowledge.article.member'].read_group([
            ('article_id', 'in', remaining_articles.root_article_id.ids), ('permission', '!=', 'none')
        ], ['article_id'], ['article_id'])  # each returned member is read on write.
        access_member_per_root_article = dict.fromkeys(remaining_articles.root_article_id.ids, 0)
        for result in results:
            access_member_per_root_article[result['article_id'][0]] += result["article_id_count"]

        for article in remaining_articles:
            # should never crash as non workspace articles always have at least one member with access.
            if access_member_per_root_article[article.root_article_id.id] > 1:
                article.category = 'shared'
            else:
                article.category = 'private'

    @api.depends('favorite_ids')
    def _compute_favorite_count(self):
        favorites = self.env['knowledge.article.favorite'].read_group(
            [('article_id', 'in', self.ids)], ['article_id'], ['article_id']
        )
        favorites_count_by_article = {
            favorite['article_id'][0]: favorite['article_id_count'] for favorite in favorites}
        for article in self:
            article.favorite_count = favorites_count_by_article.get(article.id, 0)

    @api.depends('body')
    def _compute_last_edition_data(self):
        """ Each change of body is considered as a content edition update. """
        self.last_edition_uid = self.env.uid
        self.last_edition_date = self.env.cr.now()

    @api.depends_context('uid')
    @api.depends('favorite_ids.user_id')
    def _compute_is_user_favorite(self):
        for article in self:
            favorite = article.favorite_ids.filtered(lambda f: f.user_id == self.env.user)
            article.is_user_favorite = bool(favorite)
            article.user_favorite_sequence = favorite.sequence if favorite else -1

    def _inverse_is_user_favorite(self):
        """ Read access is sufficient for toggling its own favorite status. """
        to_fav = self.filtered(lambda article: self.env.user not in article.favorite_ids.user_id)
        to_unfav = self - to_fav

        if to_fav:
            to_fav.favorite_ids = [(0, 0, {'user_id': self.env.uid})]
        if to_unfav:
            to_unfav.favorite_ids.filtered(lambda u: u.user_id == self.env.user).sudo().unlink()

    def _search_is_user_favorite(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError("Unsupported search operation on favorite articles")

        if (value and operator == '=') or (not value and operator == '!='):
            return [('favorite_ids.user_id', 'in', [self.env.uid])]

        # easier than a not in on a 2many field
        favorited = self.env['knowledge.article.favorite'].sudo().search(
            [('user_id', '=', self.env.uid)]
        ).article_id
        return [('id', 'not in', favorited.ids)]

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ Override to support ordering on is_user_favorite.

        Ordering through web client calls search_read with an order parameter set.
        Search_read then calls search. In this override we therefore override search
        to intercept a search without count with an order on is_user_favorite.
        In that case we do the search in two steps.

        First step: fill with current user's favorite results

          * Search articles that are favorite of the current user.
          * Results of that search will be at the top of returned results. Use limit
            None because we have to search all favorite articles.
          * Finally take only a subset of those articles to fill with
            results matching asked offset / limit.

        Second step: fill with other results. If first step does not gives results
        enough to match offset and limit parameters we fill with a search on other
        articles. We keep the asked domain and ordering while filtering out already
        scanned articles to keep a coherent results.

        All other search and search_read are left untouched by this override to avoid
        side effects. Search_count is not affected by this override.
        """
        if count or not order or 'is_user_favorite' not in order:
            return super(Article, self).search(args, offset=offset, limit=limit, order=order, count=count)
        order_items = [order_item.strip().lower() for order_item in (order or self._order).split(',')]
        favorite_asc = any('is_user_favorite asc' in item for item in order_items)

        # Search articles that are favorite of the current user.
        my_articles_domain = expression.AND([[('favorite_ids.user_id', 'in', [self.env.uid])], args])
        my_articles_order = ', '.join(item for item in order_items if 'is_user_favorite' not in item)
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
        # is_user_favorite when calling super() .
        article_limit = (limit - len(my_articles_ids_keep)) if limit else None
        if offset:
            article_offset = max((offset - len(articles_ids), 0))
        else:
            article_offset = 0
        article_order = ', '.join(item for item in order_items if 'is_user_favorite' not in item)

        other_article_res = super(Article, self).search(
            expression.AND([[('id', 'not in', my_articles_ids_skip)], args]),
            offset=article_offset, limit=article_limit, order=article_order, count=count
        )
        if favorite_asc in order_items:
            return other_article_res + self.browse(my_articles_ids_keep)
        else:
            return self.browse(my_articles_ids_keep) + other_article_res

    @api.model_create_multi
    def create(self, vals_list):
        """ Article permissions being quite strong, some custom behavior support
        is necessary in order to let people create articles with a correct
        configuration.

        Constraints
          * creating an article under a parent requires to be able to write on
            it. As anyway errors will raise we prevently raise a more user friendly
            error;
          * root articles without permission are forced to write to avoid issues
            with constraints;

        Notably
          * automatically organize articles to be the last of their parent
            children, unless a specific sequence is given;
          * allow creation of private articles for him- or her-self. As creation
            rights on member model are not granted, we detect private article
            creation and sudo the creation of those. This requires some data
            manipulation to sudo only those and keep requested ordering based
            on vals_list;
        """
        defaults = self.default_get(['article_member_ids', 'internal_permission', 'parent_id'])
        vals_by_parent_id = {}
        vals_as_sudo = []

        for vals in vals_list:
            can_sudo = False
            # get values from vals or defaults
            member_ids = vals.get('article_member_ids') or defaults.get('article_member_ids') or False
            internal_permission = vals.get('internal_permission') or defaults.get('internal_permission') or False
            parent_id = vals.get('parent_id') or defaults.get('parent_id') or False

            # force write permission for workspace articles
            if not parent_id and not internal_permission:
                vals.update({'internal_permission': 'write',
                             'parent_id': False,  # just be sure we don't grant privileges
                })

            # allow private articles creation if given values are considered as safe
            check_for_sudo = not self.env.su and \
                             not any(fname in vals for fname in ['favorite_ids', 'child_ids']) and \
                             not parent_id and internal_permission == 'none' and \
                             member_ids and len(member_ids) == 1
            if check_for_sudo:
                self_member = member_ids[0][0] == Command.CREATE and \
                              member_ids[0][2].get('partner_id') == self.env.user.partner_id.id
                if self_member:
                    can_sudo = True

            # if no sequence, parent will have to be checked
            if not vals.get('sequence'):
                vals_by_parent_id.setdefault(parent_id, []).append(vals)
            vals_as_sudo.append(can_sudo)

        # compute all maximum sequences / parent
        max_sequence_by_parent = {}
        if vals_by_parent_id:
            parent_ids = list(vals_by_parent_id.keys())
            try:
                self.check_access_rights('write')
                self.env['knowledge.article'].browse(parent_ids).check_access_rule('write')
            except AccessError:
                raise AccessError(_("You cannot create an article under articles on which you cannot write"))
            max_sequence_by_parent = self._get_max_sequence_inside_parents(parent_ids)

        # update sequences
        for parent_id, article_vals in vals_by_parent_id.items():
            current_sequence = 0
            if parent_id in max_sequence_by_parent:
                current_sequence = max_sequence_by_parent[parent_id] + 1

            for vals in article_vals:
                if 'sequence' in vals:
                    current_sequence = vals.get('sequence')
                else:
                    vals['sequence'] = current_sequence
                    current_sequence += 1

        # sort by sudo / not sudo
        notsudo_articles = iter(super(Article, self).create([
            vals for vals, can_sudo in zip(vals_list, vals_as_sudo)
            if not can_sudo
        ]))
        sudo_articles = iter(super(Article, self.sudo()).create([
            vals for vals, can_sudo in zip(vals_list, vals_as_sudo)
            if can_sudo
        ]).with_env(self.env))
        articles = self.env['knowledge.article']
        for vals, is_sudo in zip(vals_list, vals_as_sudo):
            if is_sudo:
                articles += next(sudo_articles)
            else:
                articles += next(notsudo_articles)

        return articles

    def write(self, vals):
        # Move under a parent is considered as a write on it (permissions, ...)
        _resequence = False
        if vals.get('parent_id'):
            parent = self.browse(vals['parent_id'])
            try:
                parent.check_access_rights('write')
                parent.check_access_rule('write')
            except AccessError:
                raise AccessError(_("You cannot move an article under %(parent_name)s as you cannot write on it",
                                    parent_name=parent.display_name))
            if 'sequence' not in vals:
                max_sequence = self._get_max_sequence_inside_parents(parent.ids).get(parent.id, -1)
                vals['sequence'] = max_sequence + 1
            else:
                _resequence = True

        result = super(Article, self).write(vals)

        # resequence only if a sequence was not already computed based on current
        # parent maximum to avoid unnecessary recomputation of sequences
        if _resequence:
            self._resequence()

        return result

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        defaults = dict(
            {"name": _("%s (copy)", self.name)},
            **(default or {})
        )
        if not self.env.su and not self.user_has_write_access:
            defaults.pop('article_member_ids', None)
            defaults.pop('favorite_ids', None)
            defaults.pop('child_ids', None)
            if self.user_has_access:
                defaults['article_member_ids'] = [
                    (0, 0, {'partner_id': self.env.user.partner_id.id,
                            'permission': 'write'})
                ]
        return super().copy(default=defaults)

    def unlink(self):
        for article in self:
            # Make all the article's children be adopted by the parent's parent.
            # Otherwise, we will have to manage an orphan house.
            parent = article.parent_id
            if parent:
                article.child_ids.write({"parent_id": parent.id})
        return super(Article, self).unlink()

    def action_archive(self):
        """ When archiving

          * archive the current article and all its writable descendants;
          * unreachable descendants (none, read) are set as free articles without
            root;
        """
        all_descendants_sudo = self.sudo()._get_descendants()
        writable_descendants = all_descendants_sudo.with_env(self.env)._filter_access_rules_python('write')
        other_descendants_sudo = all_descendants_sudo - writable_descendants

        # copy rights to allow breaking the hierarchy while keeping access for members
        for article_sudo in other_descendants_sudo:
            article_sudo._copy_access_from_parents()

        # create new root articles: direct children of archived articles that are not archived
        new_roots_woperm = other_descendants_sudo.filtered(lambda article: article.parent_id in self and not article.internal_permission)
        new_roots_wperm = other_descendants_sudo.filtered(lambda article: article.parent_id in self and article.internal_permission)
        if new_roots_wperm:
            new_roots_wperm.write({'parent_id': False})
        for new_root in new_roots_woperm:
            new_root.write({
                'internal_permission': new_root.inherited_permission,
                'parent_id': False,
            })

        return super(Article, self + writable_descendants).action_archive()

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_home_page(self):
        res_id = self.env.context.get('res_id', False)
        article = self.browse(res_id) if res_id else self._get_first_accessible_article()
        mode = 'edit' if article.user_has_write_access else 'readonly'
        action = self.env['ir.actions.act_window']._for_xml_id('knowledge.knowledge_article_action_form')
        action['res_id'] = article.id
        action['context'] = dict(
            ast.literal_eval(action.get('context')),
            form_view_initial_mode=mode,
        )
        return action

    def action_set_lock(self):
        self.is_locked = True

    def action_set_unlock(self):
        self.is_locked = False

    def action_toggle_favorite(self):
        """ Read access is sufficient for toggling its own favorite status. """
        try:
            self.check_access_rights('read')
            self.check_access_rule('read')
        except AccessError:
            # Return a meaningful error message as this may be called through UI
            raise AccessError(_("You cannot add or remove this article to your favorites"))

        self.sudo()._inverse_is_user_favorite()
        return self[0].is_user_favorite if self else False

    def action_article_archive(self):
        """ Article specific archive: after archive, redirect to the home page
        displaying accessible articles, instead of doing nothing. """
        self.action_archive()
        return self.with_context(res_id=False).action_home_page()

    def action_unarchive(self):
        res = super(Article, self).action_unarchive()
        if len(self) == 1:
            return self.with_context(res_id=self.id).action_home_page()
        return res

    # ------------------------------------------------------------
    # SEQUENCE / ORDERING
    # ------------------------------------------------------------

    def move_to(self, parent_id=False, before_article_id=False, is_private=False):
        """ Move an article in the tree.

        :param int parent_id: id of an article that will be the new parent;
        :param int before_article_id: id of an article before which the article
          should be moved. Otherwise it is put as last parent children;
        :param bool is_private: set as private;
        """
        self.ensure_one()
        parent = self.browse(parent_id)
        before_article = self.browse(before_article_id)

        values = {'parent_id': parent_id}
        if before_article:
            values['sequence'] = before_article.sequence
        if not parent_id:
            # be sure to have an internal permission on the article if moved outside
            # of an hierarchy
            values.update({
                'internal_permission': 'none' if is_private else 'write',
                'is_desynchronized': False
            })

        # if set as standalone private: remove members, ensure current user is the
        # only member -> require sudo to bypass member ACLs
        if not parent and is_private:
            # explicitly check for rights before going into sudo
            try:
                self.check_access_rights('write')
                (self + parent).check_access_rule('write')
            except:
                raise AccessError(
                    _("You are not allowed to move this article under article %(parent_name)s",
                      parent_name=parent.display_name)
                )
            self_sudo = self.sudo()
            self_member = self_sudo.article_member_ids.filtered(lambda m: m.partner_id == self.env.user.partner_id)
            member_command = [(2, member.id) for member in self_sudo.article_member_ids if member.partner_id != self.env.user.partner_id]
            if self_member:
                member_command.append((1, self_member.id, {'permission': 'write'}))
            else:
                member_command.append((0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                }))
            values['article_member_ids'] = member_command
            return self_sudo.write(values)
        return self.write(values)

    def _resequence(self):
        """ This method reorders the children of the same parent (brotherhood) if
        needed. If an article have been moved from one parent to another we do not
        need to resequence the children of the old parent as the order remains
        unchanged. We only need to resequence the children of the new parent only if
        the sequences of the children contains duplicates.

        When reordering an article, we assume that we always set the sequence
        equals to the position we want it to be. When duplicates last modified
        wins. We use write date, presence in self (indicating a write hence a
        priority) and ID to differentiate new ordering between duplicates.

        e.g. if we want article D to be placed at 3rd position between A B et C
          * set D.sequence = 2;
          * but C was already 2;
          * D is in self: it wins. Or D has newer write_date: it wins. Or D has
            been created more recently: it wins.
        """
        parent_ids = self.mapped("parent_id").ids
        if any(not article.parent_id for article in self):
            parent_ids.append(False)

        # fetch and sort all_chidren: sequence ASC, then modified, then write date DESC
        all_children = self.search([("parent_id", 'in', parent_ids)])
        all_children = all_children.sorted(
            lambda article: (-1 * article.sequence,
                             article in self,
                             article.write_date,
                             article.id
                             ),
            reverse=True  # due to date
        )

        article_to_update_by_sequence = defaultdict(self.env['knowledge.article'].browse)
        for parent_id in parent_ids:
            children = all_children.filtered(lambda a: a.parent_id.id == parent_id)
            sequences = children.mapped('sequence')
            # no need to resequence if no duplicates.
            if len(sequences) == len(set(sequences)):
                return

            # only need to resequence after duplicate: allow holes in the sequence but limit number of write operations.
            duplicate_index = [idx for idx, item in enumerate(sequences) if item in sequences[:idx]][0]
            start_sequence = sequences[duplicate_index] + 1
            for i, child in enumerate(children[duplicate_index:]):
                article_to_update_by_sequence[i + start_sequence] |= child

        for sequence in article_to_update_by_sequence:
            # call super to avoid loops in write
            super(Article, article_to_update_by_sequence[sequence]).write({'sequence': sequence})

    @api.model
    def _get_max_sequence_inside_parents(self, parent_ids):
        max_sequence_by_parent = {}
        rg_results = self.env['knowledge.article'].sudo().read_group(
            [('parent_id', 'in', parent_ids)],
            ['sequence:max'],
            ['parent_id']
        )
        for rg_line in rg_results:
            # beware name_get like returns either 0, either (id, 'name')
            index = rg_line['parent_id'][0] if rg_line['parent_id'] else False
            max_sequence_by_parent[index] = rg_line['sequence']
        return max_sequence_by_parent

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    @api.model
    @api.returns('knowledge.article', lambda article: article.id)
    def article_create(self, title=False, parent_id=False, is_private=False):
        """ Helper to create articles, allowing to pre-compute some configuration
        values.

        :param str title: name of the article;
        :param int parent_id: id of an existing article who will be the parent
          of the newly created articled. Must be writable;
        :param bool is_private: set current user as sole owner of the new article;
        """
        parent = self.browse(parent_id) if parent_id else self.env['knowledge.article']
        values = {'parent_id': parent.id}
        if title:
            values.update({
                'body': Markup('<h1>%s</h1>') % title,
                'name': title,
            })
        else:
            values['body'] = Markup('<h1 class="oe-hint"><br></h1>')

        if parent:
            if not is_private and parent.category == "private":
                is_private = True
        else:
            # child do not have to setup an internal permission as it is inherited
            values['internal_permission'] = 'none' if is_private else 'write'

        if is_private:
            if parent and parent.category != "private":
                raise ValidationError(
                    _("Cannot create an article under article %(parent_name)s which is a non-private parent",
                      parent_name=parent.display_name)
                )
            if not parent:
                values['article_member_ids'] = [(0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                })]
        return self.create(values)

    def get_user_sorted_articles(self, search_query, limit=10):
        """ Called when using the Command palette to search for articles matching the search_query.
        As the article should be sorted also in function of the current user's favorite sequence, a search_read rpc
        won't be enough to returns the articles in the correct order.
        This method returns a list of article proposal matching the search_query sorted by:
            - is_user_favorite - by Favorite sequence
            - Favorite count
        and returned result mimic a search_read result structure.
        """
        search_domain = ["|", ("name", "ilike", search_query), ("root_article_id.name", "ilike", search_query)]
        articles = self.search(
            expression.AND([search_domain, [("is_user_favorite", "=", True)]]),
            limit=limit
        )
        sorted_articles = articles.sorted(
            key=lambda a: (-1 * a.user_favorite_sequence,
                           a.favorite_count,
                           a.write_date,
                           a.id),
            reverse=True
        )

        # fill with not favorites articles
        if len(sorted_articles) < limit:
            articles = self.search(
                expression.AND([search_domain, [("is_user_favorite", "=", False)]]),
                limit=(limit-len(sorted_articles))
            )
            sorted_articles += articles.sorted(
                key=lambda a: (a.favorite_count,
                               a.write_date,
                               a.id),
                reverse=True
            )

        return sorted_articles.read(['id', 'name', 'is_user_favorite',
                                     'favorite_count', 'root_article_id', 'icon'])

    # ------------------------------------------------------------
    # PERMISSIONS / MEMBERS
    # ------------------------------------------------------------

    def restore_article_access(self):
        """ Resets permissions based on ancestors. It removes all members except
        members on the articles that are not on any ancestor or that have higher
        permission than from ancestors. """
        self.ensure_one()
        if not self.parent_id:
            return False
        if not self.env.su and not self.user_has_write_access:
            raise AccessError(_('You cannot restore the article %(article_name)s',
                                article_name=self.display_name))
        member_permission = (self | self.parent_id)._get_article_member_permissions()
        article_members_permission = member_permission[self.id]
        parents_members_permission = member_permission[self.parent_id.id]

        members_values = []
        for partner, values in article_members_permission.items():
            permission = values['permission']
            if values["based_on"] or partner not in parents_members_permission \
                or ARTICLE_PERMISSION_LEVEL[permission] > ARTICLE_PERMISSION_LEVEL[parents_members_permission[partner]['permission']]:
                continue
            members_values.append((3, values['member_id']))

        return self.sudo().write({
            'internal_permission': False,
            'article_member_ids': members_values,
            'is_desynchronized': False
        })

    def invite_members(self, partners, permission):
        """ Invite the given partners to the current article. Inviting to remove
        access is straightforward (just set permission). Inviting with rights
        requires to check for privilege escalation in descendants.

        :param Model<res.partner> partner_ids: recordset of invited partners;
        :param string permission: permission of newly invited members, one of
          'none', 'read' or 'write';
        """
        self.ensure_one()
        if permission == 'none':
            self._add_members(partners, permission)
        else:
            # prevent the invited user to get access to children articles the current user has no access to
            unreachable_children = self.sudo().child_ids.filtered(lambda c: not c.user_has_write_access)
            for child in unreachable_children:
                child._add_members(partners, 'none', force_update=False)

            share_partner_ids = partners.filtered(lambda partner: partner.partner_share)
            self._add_members(share_partner_ids, 'read')
            self._add_members(partners - share_partner_ids, permission)

        if permission != 'none':
            self._send_invite_mail(partners)

        return True

    def _set_internal_permission(self, permission):
        """ Set the internal permission of the article.

        Special cases:
          * to ensure the user still has write access after modification,
            add the user as write member if given permission != write;
          * when downgrading internal permission on a child article, desync it
            from parent to stop inherited rights transmission;
          * if we set same permission as parent and the article has no specific
            member: resync if on parent;

        :param str permission: internal permission to set, one of 'none', 'read'
          or 'write';
        """
        self.ensure_one()
        if self.user_has_write_access and permission != "write":
            self._add_members(self.env.user.partner_id, 'write')

        downgrade = not self.is_desynchronized and self.parent_id and \
                    ARTICLE_PERMISSION_LEVEL[self.parent_id.inherited_permission] > ARTICLE_PERMISSION_LEVEL[permission]
        if downgrade:
            return self._desync_access_from_parents(force_internal_permission=permission)

        values = {'internal_permission': permission}
        if permission == self.parent_id.inherited_permission and not self.article_member_ids:
            values.update({
                'internal_permission': False,
                'is_desynchronized': False
            })
        return self.write(values)

    def _set_member_permission(self, member, permission, is_based_on=False):
        """ Sets the given permission to the given member.

        If the member has rights based on membership: simply update it.

        If the member has rights based on a parent article (inherited rights)
          If the new permission is downgrading the member's access
            the article is desynchronized form its parent;
          Else we add a new member with the higher permission;

        :param <knowledge.article.member> member: member whose permission
          is to be updated. Can be a member of 'self' or one of its ancestors;
        :param str permission: new permission, one of 'none', 'read' or 'write';
        :param bool is_based_on: whether rights are inherited or through membership;
        """
        self.ensure_one()
        if is_based_on:
            downgrade = ARTICLE_PERMISSION_LEVEL[member.permission] > ARTICLE_PERMISSION_LEVEL[permission]
            if downgrade:
                self._desync_access_from_parents(force_partners=member.partner_id, force_member_permission=permission)
            else:
                self._add_members(member.partner_id, permission)
        else:
            member.sudo().write({'permission': permission})

    def _remove_member(self, member):
        """ Removes a member from the article. If the member was based on a
        parent article, the current article will be desynchronized form its parent.
        We also ensure the partner to remove is removed after the desynchronization
        if was copied from parent.

        :param <knowledge.article.member> member: member to remove
        """
        self.ensure_one()
        if not member:
            raise ValueError(_('Trying to remove wrong member.'))

        # belongs to current article members
        current_membership = self.article_member_ids.filtered(lambda m: m == member)

        current_user_partner = self.env.user.partner_id
        remove_self = member.partner_id == current_user_partner
        # If remove self member, set member permission to 'none' (= leave article) to hide the article for the user.
        if remove_self:
            if current_membership:
                members_command = [(1, current_membership.id, {'permission': 'none'})]
            else:
                members_command = [(0, 0, {'partner_id': current_user_partner.id, 'permission': 'none'})]
            self.sudo().write({'article_member_ids': members_command})
        # member to remove is on the article itself. Simply remove the member.
        elif current_membership:
            if not self.env.su and not self.user_has_write_access:
                raise AccessError(
                    _("You cannot remove the member %(member_name)s from article %(article_name)s",
                      member_name=member.display_name,
                      article_name=self.display_name
                      ))
            self.sudo().write({'article_member_ids': [(2, current_membership.id)]})
        # Inherited rights from parent
        else:
            self._desync_access_from_parents(force_partners=self.article_member_ids.partner_id)
            current_membership = self.article_member_ids.filtered(lambda m: m.partner_id == member.partner_id)
            if current_membership:
                self.sudo().write({'article_member_ids': [(2, current_membership.id)]})

    def _add_members(self, partners, permission, force_update=True):
        """ Adds new members to the current article with the given permission.
        If a given partner is already member permission is updated instead.

        :param <res.partner> partners: recordset of res.partner for which
          new members are added;
        :param string permission: member permission, one of 'none', 'read' or 'write';
        :param boolean force_update: if already existing, force the new permission;
          this can be used to create default members and left existing one untouched;
        """
        self.ensure_one()
        if not self.env.su and not self.user_has_write_access:
            raise AccessError(
                _("You cannot give access to the article '%s' as you are not editor.", self.name))

        members_to_update = self.article_member_ids.filtered_domain([('partner_id', 'in', partners.ids)])
        partners_to_create = partners - members_to_update.mapped('partner_id')

        members_command = [
            (0, 0, {'partner_id': partner.id,
                    'permission': permission})
            for partner in partners_to_create
        ]
        if force_update:
            members_command += [
                (1, member.id, {'permission': permission})
                for member in members_to_update
            ]

        return self.sudo().write({'article_member_ids': members_command})

    def _desync_access_from_parents(self, force_internal_permission=False,
                                    force_partners=False, force_member_permission=False):
        """ Copies copy all inherited accesses from parents on the article and
        de-synchronize the article from its parent, allowing custom access management.
        We allow to force permission of given partners.

        :param string force_internal_permission: force a new internal permission
          for the article. Otherwise fallback on inherited computed internal
          permission;
        :param <res.partner> force_partners: force permission of new members
          related to those partners;
        :param string force_member_permission: used with force_partners to specify
          the custom permission to give. One of 'none', 'read', 'write';
        """
        self.ensure_one()
        new_internal_permission = force_internal_permission or self.inherited_permission
        members_commands = self._copy_access_from_parents(
            force_partners=force_partners,
            force_member_permission=force_member_permission
        )

        return self.sudo().write({
            'article_member_ids': members_commands,
            'internal_permission': new_internal_permission,
            'is_desynchronized': True,
        })

    def _copy_access_from_parents(self, force_partners=False, force_member_permission=False):
        """ Copies copy all inherited accesses from parents on the article and
        de-synchronize the article from its parent, allowing custom access management.
        We allow to force permission of given partners.

        :param string force_internal_permission: force a new internal permission
          for the article. Otherwise fallback on inherited computed internal
          permission;
        :param <res.partner> force_partners: force permission of new members
          related to those partners;
        """
        self.ensure_one()
        members_permission = self._get_article_member_permissions()[self.id]

        members_commands = []
        for partner_id, values in members_permission.items():
            # if member already on self, do not add it.
            if not values['based_on'] or values['based_on'] == self.id:
                continue
            if force_partners and force_member_permission and partner_id in force_partners.ids:
                new_member_permission = force_member_permission
            else:
                new_member_permission = values['permission']

            members_commands.append(
                (0, 0, {'partner_id': partner_id,
                        'permission': new_member_permission,
                       }))
        return members_commands

    @api.model
    def _get_internal_permission(self, filter_domain=None):
        """ Compute article based permissions.

        Note: we don't use domain because we cannot include properly the where clause
        in the custom sql query. The query's output table and fields names does not match
        the model we are working on.
        """
        self.flush_model()

        args = []
        base_where_domain = ''
        if self.ids:
            base_where_domain = "WHERE id in %s"
            args.append(tuple(self.ids))

        where_clause = ''
        if filter_domain:
            query = self.with_context(active_test=False)._where_calc(filter_domain)
            table_name, where_clause, where_params = query.get_sql()
            where_clause = f'WHERE {where_clause.replace(table_name, "article_perms")}'
            args += where_params

        sql = f'''
    WITH RECURSIVE article_perms as (
        SELECT id, id as article_id, parent_id, internal_permission, is_desynchronized
          FROM knowledge_article
          {base_where_domain}
         UNION
        SELECT parents.id, perms.article_id, parents.parent_id,
               COALESCE(perms.internal_permission, parents.internal_permission),
               perms.is_desynchronized
          FROM knowledge_article parents
    INNER JOIN article_perms perms
            ON perms.parent_id=parents.id
               AND perms.is_desynchronized IS NOT TRUE
               AND perms.internal_permission IS NULL
    )
    SELECT article_id, max(internal_permission)
      FROM article_perms
           {where_clause}
  GROUP BY article_id'''
        self._cr.execute(sql, args)
        return dict(self._cr.fetchall())

    @api.model
    def _get_partner_member_permissions(self, partner):
        """ Retrieve the permission for the given partner for all articles.
        The articles can be filtered using the article_ids param.

        The member model is fully flushed before running the request. """
        self.env['knowledge.article'].flush_model()
        self.env['knowledge.article.member'].flush_model()

        args = [partner.id]
        base_where_domain = ''
        if self.ids:
            base_where_domain = "WHERE perms1.id in %s"
            args.append(tuple(self.ids))

        sql = f'''
    WITH RECURSIVE article_perms as (
        SELECT a.id, a.parent_id, m.permission, a.is_desynchronized
          FROM knowledge_article a
     LEFT JOIN knowledge_article_member m
            ON a.id=m.article_id and partner_id = %s
    ), article_rec as (
        SELECT perms1.id, perms1.id as article_id, perms1.parent_id,
               perms1.permission, perms1.is_desynchronized
          FROM article_perms as perms1
          {base_where_domain}
         UNION
        SELECT perms2.id, perms_rec.article_id, perms2.parent_id,
               COALESCE(perms_rec.permission, perms2.permission),
               perms2.is_desynchronized
          FROM article_perms as perms2
    INNER JOIN article_rec perms_rec
            ON perms_rec.parent_id=perms2.id
               AND perms_rec.is_desynchronized IS NOT TRUE
               AND perms_rec.permission IS NULL
    )
    SELECT article_id, max(permission)
      FROM article_rec
     WHERE permission IS NOT NULL
  GROUP BY article_id'''
        self._cr.execute(sql, args)
        return dict(self._cr.fetchall())

    def _get_article_member_permissions(self, additional_fields=False):
        """ Retrieve the permission for all the members that apply to the target article.
        Members that apply are not only the ones on the article but can also come from parent articles.

        The caller can pass additional fields to retrieve from the following models:
        - res.partner, joined on the partner_id of the membership
        - knowledge.article, joined on the 'origin' of the membership
          (when the membership is based on one of its parent article)
          to retrieve more fields on the origin of the membership
        - knowledge.article.member to retrieve more fields on the membership

        The expected format is::

            {'model': [('field', 'field_alias')]}
        e.g::
            {
                'res.partner': [
                    ('name', 'partner_name'),
                    ('email', 'partner_email'),
                ]
            }

        Please note that these additional fields are not sanitized, the caller
        has the responsibility to check that user can access those fields and
        that no injection is possible. """
        self.env['res.partner'].flush_model()
        self.env['knowledge.article'].flush_model()
        self.env['knowledge.article.member'].flush_model()

        add_where_clause = ''
        args = []
        if self.ids:
            args = [tuple(self.ids)]
            add_where_clause += " AND article_id in %s"

        additional_select_fields = ''
        join_clause = ''
        if additional_fields:
            supported_additional_models = [
                'res.partner',
                'knowledge.article',
                'knowledge.article.member',
            ]

            # 1. build the join clause based on the given models (additional_fields keys)
            join_clauses = []
            for model in additional_fields.keys():
                if model not in supported_additional_models:
                    continue

                table_name = self.env[model]._table
                join_condition = ''
                if model == 'res.partner':
                    join_condition = f'{table_name}.id = partner_id'
                elif model == 'knowledge.article':
                    join_condition = f'{table_name}.id = origin_id'
                elif model == 'knowledge.article.member':
                    join_condition = f'{table_name}.id = member_id'

                join_clauses.append(f'LEFT OUTER JOIN {table_name} ON {join_condition}')

            join_clause = ' '.join(join_clauses)

            # 2. build the select clause based on the given fields/aliases pairs
            # (additional_fields values)
            select_fields = []
            for model, fields_list in additional_fields.items():
                if model not in supported_additional_models:
                    continue

                table_name = self.env[model]._table
                for (field, field_alias) in fields_list:
                    select_fields.append(f'{table_name}.{field} as {field_alias}')

            additional_select_fields = ', %s' % ', '.join(select_fields)

        sql = f'''
    WITH article_permission as (
        WITH RECURSIVE article_perms as (
            SELECT a.id, a.parent_id, m.id as member_id, m.partner_id,
                   m.permission
              FROM knowledge_article a
         LEFT JOIN knowledge_article_member m
                ON a.id = m.article_id
        ), article_rec as (
            SELECT perms1.id, perms1.id as article_id, perms1.parent_id,
                   perms1.member_id, perms1.partner_id, perms1.permission,
                   perms1.id as origin_id, 0 as level
              FROM article_perms as perms1
             UNION
            SELECT perms2.id, perms_rec.article_id, perms2.parent_id,
                   perms2.member_id, perms2.partner_id, perms2.permission,
                   perms2.id as origin_id, perms_rec.level + 1
              FROM article_perms as perms2
        INNER JOIN article_rec perms_rec
                ON perms_rec.parent_id=perms2.id
        )
        SELECT article_id, origin_id, member_id, partner_id,
               permission, min(level) as min_level
          FROM article_rec
         WHERE partner_id is not null
               {add_where_clause}
      GROUP BY article_id, origin_id, member_id, partner_id, permission
    )
    SELECT article_id, origin_id, member_id, partner_id, permission, min_level
           {additional_select_fields}
    FROM article_permission
    {join_clause}
        '''

        self._cr.execute(sql, args)
        results = self._cr.dictfetchall()

        # Now that we have, for each article, all the members found on themselves and their parents.
        # We need to keep only the first partners found (lowest level) for each article
        article_members = defaultdict(dict)
        min_level_dict = defaultdict(dict)

        _nolevel = -1
        for result in results:
            article_id = result['article_id']
            origin_id = result['origin_id']
            partner_id = result['partner_id']
            level = result['min_level']
            min_level = min_level_dict[article_id].get(partner_id, _nolevel)
            if min_level == _nolevel or level < min_level:
                article_members[article_id][partner_id] = {
                    'member_id': result['member_id'],
                    'based_on': origin_id if origin_id != article_id else False,
                    'permission': result['permission']
                }
                min_level_dict[article_id][partner_id] = level

                if additional_fields:
                    # update our resulting dict based on additional fields
                    article_members[article_id][partner_id].update({
                        field_alias: result[field_alias] if model != 'knowledge.article' or origin_id != article_id else False
                        for model, fields_list in additional_fields.items()
                        for (field, field_alias) in fields_list
                    })
        # add empty member for each article that doesn't have any.
        for article in self:
            if article.id not in article_members:
                article_members[article.id][None] = {'based_on': False, 'member_id': False, 'permission': None}

                if additional_fields:
                    # update our resulting dict based on additional fields
                    article_members[article.id][None].update({
                        field_alias: False
                        for model, fields_list in additional_fields.items()
                        for (field, field_alias) in fields_list
                    })

        return article_members

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _mail_track(self, tracked_fields, initial):
        changes, tracking_value_ids = super(Article, self)._mail_track(tracked_fields, initial)
        if {'parent_id', 'root_article_id'} & changes and not self.user_has_write_access:
            partner_name = self.env.user.partner_id.display_name
            message_body = _("Logging changes from %(partner_name)s without write access on article %(article_name)s due to hierarchy tree update",
                partner_name=partner_name, article_name=self.display_name)
            self._track_set_log_message("<p>%s</p>" % message_body)
        return changes, tracking_value_ids

    def _send_invite_mail(self, partners):
        # TDE NOTE: try to cleanup and batchize
        self.ensure_one()
        for partner in partners:
            subject = _("Invitation to access %s", self.name)
            partner_lang = get_lang(self.env, lang_code=partner.lang).code
            body = self.env['ir.qweb'].with_context(lang=partner_lang)._render(
                'knowledge.knowledge_article_mail_invite', {
                    'record': self,
                    'user': self.env.user,
                    'recipient': partner,
                    'link': self._get_invite_url(partner),
                })

            self.with_context(lang=partner_lang).message_notify(
                body=body,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=partner.ids,
                subject=subject,
            )

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_invite_url(self, partner):
        self.ensure_one()
        member = self.env['knowledge.article.member'].search([('article_id', '=', self.id), ('partner_id', '=', partner.id)])
        return url_join(self.get_base_url(), "/knowledge/article/invite/%s/%s" % (member.id, member._get_invitation_hash()))

    def _get_first_accessible_article(self):
        """ Returns the first accessible article for the current user.
        If user has favorites, return first favorite article. """
        article = self.env['knowledge.article']
        if not self.env.user._is_public():
            article = self.env['knowledge.article.favorite'].search([
                ('user_id', '=', self.env.uid), ('article_id.active', '=', True)
            ], limit=1).article_id
        if not article:
            # retrieve workspace articles first, then private/shared ones.
            article = self.search([
                ('parent_id', '=', False)
            ], limit=1, order='sequence, internal_permission desc')
        return article

    def get_valid_parent_options(self, search_term=""):
        """ Returns the list of articles that can be set as parent for the
        current article (to avoid recursions) """
        return self.search_read(
            domain=['&',
                    ['name', 'ilike', search_term],
                    ['id', 'not in', (self._get_descendants() + self).ids]
                    ],
            fields=['id', 'display_name', 'root_article_id'],
            limit=15,
        )

    def _get_descendants(self):
        """ Returns the descendants recordset of the current article. """
        return self.env['knowledge.article'].search([('id', 'not in', self.ids), ('parent_id', 'child_of', self.ids)])

    def _get_readable_ancetors(self):
        """ Returns the parents recordset of the current article. Do the computation
        as sudo """
        self.ensure_one()
        ancestors = self.env['knowledge.article'].sudo()
        current = self.sudo().parent_id
        while current:
            ancestors += current
            current = current.parent_id
        return ancestors._filter_access_rules_python('read').with_env(self.env)
