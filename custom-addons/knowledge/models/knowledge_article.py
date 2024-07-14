# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import json
import re

from collections import defaultdict
from datetime import datetime, timedelta
from lxml import html
from markupsafe import Markup
from urllib import parse
from werkzeug.urls import url_join

from odoo import api, Command, fields, models, _
from odoo.addons.web_editor.tools import handle_history_divergence
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.osv import expression
from odoo.tools import get_lang, is_html_empty
from odoo.tools.translate import html_translate
from odoo.tools.sql import SQL

ARTICLE_PERMISSION_LEVEL = {'none': 0, 'read': 1, 'write': 2}


class Article(models.Model):
    _name = "knowledge.article"
    _description = "Knowledge Article"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'html.field.history.mixin']
    _order = "favorite_count desc, write_date desc, id desc"
    _mail_post_access = 'read'
    _parent_store = True

    def _get_versioned_fields(self):
        return [Article.body.name]

    DEFAULT_ARTICLE_TRASH_LIMIT_DAYS = 30

    active = fields.Boolean(default=True)
    name = fields.Char(string="Title", tracking=20, default_export_compatible=True)
    body = fields.Html(string="Body", prefetch=False)
    icon = fields.Char(string='Emoji')
    cover_image_id = fields.Many2one("knowledge.cover", string='Article cover')
    cover_image_url = fields.Char(related="cover_image_id.attachment_url", string="Cover url")
    cover_image_position = fields.Float(string="Cover vertical offset")
    is_locked = fields.Boolean(
        string='Locked',
        help="When locked, users cannot write on the body or change the title, "
             "even if they have write access on the article.")
    full_width = fields.Boolean(
        string='Full width',
        help="When set, the article body will take the full width available on the article page. "
             "Otherwise, the body will have large horizontal margins.")
    article_url = fields.Char('Article URL', compute='_compute_article_url', readonly=True)
    # Access rules and members + implied category
    internal_permission = fields.Selection(
        [('write', 'Can edit'), ('read', 'Can read'), ('none', 'Restricted')],
        string='Internal Permission', required=False,
        help="Default permission for all internal users. "
             "(External users can still have access to this article if they are added to its members)")
    inherited_permission = fields.Selection(
        [('write', 'Can edit'), ('read', 'Can read'), ('none', 'Restricted')],
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
    user_has_access_parent_path = fields.Boolean(
        string='Can the user join?', compute='_compute_user_has_access_parent_path', recursive=True,
        help="Has the user access to each parent from current article until its root?",
    )
    user_has_write_access = fields.Boolean(
        string='Has Write Access',
        compute="_compute_user_has_write_access", search="_search_user_has_write_access")
    user_can_read = fields.Boolean(string='Can Read', compute='_compute_user_can_read')  # ACL-like
    user_can_write = fields.Boolean(string='Can Edit', compute='_compute_user_can_write')  # ACL-like
    user_permission = fields.Selection(
        [('write', 'write'), ('read', 'read'), ('none', 'none')],
        string='User permission',
        compute='_compute_user_permission')
    # Hierarchy and sequence
    parent_id = fields.Many2one(
        "knowledge.article", string="Parent Article", tracking=30,
        ondelete="cascade")
    # used to speed-up hierarchy operators such as child_of/parent_of
    # see '_parent_store' implementation in the ORM for details
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        "knowledge.article", "parent_id", string="Child Articles and Items",
        copy=True)
    has_item_parent = fields.Boolean('Is the parent an Item?', related='parent_id.is_article_item')
    has_item_children = fields.Boolean('Has article item children?', compute="_compute_has_article_children")
    has_article_children = fields.Boolean('Has normal article children?', compute="_compute_has_article_children")
    is_desynchronized = fields.Boolean(
        string="Desyncronized with parents",
        help="If set, this article won't inherit access rules from its parents anymore.")
    sequence = fields.Integer(
        string="Sequence",
        default=0,  # Set default=0 to avoid false values and messed up sequence order inside same parent
        help="The sequence is computed only among the articles that have the same parent.")
    root_article_id = fields.Many2one(
        'knowledge.article', string="Menu Article", recursive=True,
        compute="_compute_root_article_id", store=True, compute_sudo=True, tracking=10,
        help="The subject is the title of the highest parent in the article hierarchy.")
    # Item management
    is_article_item = fields.Boolean('Is Item?', index=True)
    stage_id = fields.Many2one('knowledge.article.stage', string="Item Stage",
        compute='_compute_stage_id', store=True, readonly=False, tracking=True,
        group_expand='_read_group_stage_ids', domain="[('parent_id', '=', parent_id)]")

    # categories and ownership
    category = fields.Selection(
        [('workspace', 'Workspace'), ('private', 'Private'), ('shared', 'Shared')],
        compute="_compute_category", compute_sudo=True, store=True, index=True, string="Section",
        help='Used to categozie articles in UI, depending on their main permission definitions.')
        # Stored to improve performance when loading the article tree. (avoid looping through members if 'workspace')
    # Same as write_uid/_date but limited to the body
    last_edition_uid = fields.Many2one(
        "res.users", string="Last Edited by", readonly=True, copy=False)
    last_edition_date = fields.Datetime(
        string="Last Edited on", readonly=True, copy=False)
    # Favorite
    is_user_favorite = fields.Boolean(
        string="Is Favorited",
        compute="_compute_is_user_favorite",
        search="_search_is_user_favorite")
    user_favorite_sequence = fields.Integer(string="User Favorite Sequence", compute="_compute_is_user_favorite")
    favorite_ids = fields.One2many(
        'knowledge.article.favorite', 'article_id',
        string='Favorite Articles', copy=False)
    # Set default=0 to avoid false values and messed up order
    favorite_count = fields.Integer(
        string="#Is Favorite",
        compute="_compute_favorite_count", store=True, copy=False, default=0)
    # Visibility
    is_article_visible_by_everyone = fields.Boolean(
        string="Can everyone see the Article?", compute="_compute_is_article_visible_by_everyone",
        readonly=False, recursive=True, store=True,
    )
    is_article_visible = fields.Boolean(
        string='Can the user see the article?', compute='_compute_is_article_visible',
        search='_search_is_article_visible', recursive=True
    )
    # Trash management
    to_delete = fields.Boolean(string="Trashed", tracking=100,
        help="""When sent to trash, articles are flagged to be deleted
                days after last edit. knowledge_article_trash_limit_days config
                parameter can be used to modify the number of days. 
                (default is 30)""")
    deletion_date = fields.Date(string="Deletion Date", compute="_compute_deletion_date")
    # Property fields
    article_properties_definition = fields.PropertiesDefinition('Article Item Properties')
    article_properties = fields.Properties('Properties', definition="parent_id.article_properties_definition", copy=True)

    # Templates
    is_template = fields.Boolean(string="Is Template")
    template_body = fields.Text(string="Template Body", translate=html_translate)
    template_category_id = fields.Many2one("knowledge.article.template.category", string="Template Category",
        compute="_compute_template_category_id", inverse="_inverse_template_category_id", store=True)
    template_category_sequence = fields.Integer(string="Template Category Sequence", related="template_category_id.sequence")
    template_description = fields.Char(string="Template Description", translate=True)
    template_name = fields.Char(string="Template Title", translate=True)
    template_preview = fields.Html(string="Template Preview", compute="_compute_template_preview")
    template_sequence = fields.Integer(string="Template Sequence", help="It determines the display order of the template within its category")

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
        ('check_article_item_parent',
         'check(is_article_item IS NOT TRUE OR parent_id IS NOT NULL)',
         'Article items must have a parent.'
         ),
        ('check_trash',
         'check(to_delete IS NOT TRUE or active IS NOT TRUE)',
         'Trashed articles must be archived.'
        ),
        ('check_template_category_on_root',
         'check(is_template IS NOT TRUE OR parent_id IS NOT NULL OR template_category_id IS NOT NULL)',
         'Root templates must have a category.'
        ),
        ('check_template_name_required',
         'check(is_template IS NOT TRUE OR template_name IS NOT NULL)',
         'Templates should have a name.'
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
            if article.inherited_permission != 'write' and not article._has_write_member():
                raise ValidationError(_("The article '%s' needs at least one member with 'Write' access.", article.display_name))

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise ValidationError(
                _('Articles %s cannot be updated as this would create a recursive hierarchy.',
                  ', '.join(self.mapped('name'))
                 )
            )

    @api.constrains('is_template', 'parent_id')
    def _check_template_hierarchy(self):
        for article in self:
            if not article.parent_id:
                continue
            if article.is_template and not article.parent_id.is_template:
                raise ValidationError(
                    _('"%(article_name)s" is a template and can not be a child of an article ("%(parent_article_name)s").',
                        article_name=article.name,
                        parent_article_name=article.parent_id.name
                    )
                )
            if not article.is_template and article.parent_id.is_template:
                raise ValidationError(
                    _('"%(article_name)s" is an article and can not be a child of a template ("%(parent_article_name)s")."',
                        article_name=article.name,
                        parent_article_name=article.parent_id.name
                    )
                )

    # ------------------------------------------------------------
    # COMPUTED FIELDS
    # ------------------------------------------------------------

    def _compute_article_url(self):
        for article in self:
            if not article.ids:
                article.article_url = False
            else:
                article.article_url = url_join(article.get_base_url(), 'knowledge/article/%s' % article.id)

    @api.depends('child_ids', 'child_ids.is_article_item')
    def _compute_has_article_children(self):
        results = self.env['knowledge.article']._read_group(
            [('parent_id', 'in', self.ids)],
            ['parent_id', 'is_article_item'])
        count_by_article_id = {(parent.id, is_article_item) for parent, is_article_item in results}
        for article in self:
            article.has_item_children = (article.id, True) in count_by_article_id
            article.has_article_children = (article.id, False) in count_by_article_id

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

    @api.depends('parent_id', 'is_article_item')
    def _compute_stage_id(self):
        articles = self.filtered(lambda article: not article.is_article_item)
        articles.stage_id = False
        if articles == self:
            return

        # Put the new article(s) in the first stage (specific by parent_id)
        items = self - articles
        results = self.env['knowledge.article.stage'].search_read(
            [('parent_id', 'in', items.parent_id.ids)],
            ['parent_id', 'id'])
        stages_by_parent_id = dict()
        # keep only the first stage by parent_id
        for result in results:
            parent_id = result['parent_id'][0] if result.get('parent_id') else False
            if parent_id and not stages_by_parent_id.get(parent_id):
                stages_by_parent_id[parent_id] = result['id']
        for item in items:
            item.stage_id = stages_by_parent_id.get(item.parent_id.id)

    @api.depends('parent_id')
    def _compute_template_category_id(self):
        self._propagate_template_category_id()

    def _inverse_template_category_id(self):
        self._propagate_template_category_id()

    def _propagate_template_category_id(self):
        """ The templates inherit the category from their parents. This method will
            ensure that the categories will be consistent over the whole template
            hierarchy. To update the category of a template, the user will have to
            update the category of the root template. """
        for article in self:
            if article.parent_id:
                article.template_category_id = article.parent_id.template_category_id
            for child in article.child_ids:
                child.template_category_id = article.template_category_id

    @api.depends('template_body')
    def _compute_template_preview(self):
        for template in self:
            template.template_preview = template._render_template()

    @api.depends('parent_id', 'parent_id.inherited_permission_parent_id', 'internal_permission')
    def _compute_inherited_permission(self):
        """ Computed inherited internal permission. We go up ancestors until
        finding an article with an internal permission set, or a root article
        (without parent) or until finding a desynchronized article which
        serves as permission ancestor. Desynchronized articles break the
        permission tree finding.

        'parent_id.inherited_permission_parent_id' needs to be in the trigger
        as we will need to update this article's inherited permissions if our parent
        changes itself from which article it's inheriting.
        This allows cascading changes "downwards" when we modify the
        internal_permission of an article in the chain.

        It is however not directly used as we optimize the batching and group all
        articles by their parent_id."""
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
        Article = self.env["knowledge.article"]
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError("Unsupported search operator")

        articles_with_access = {}
        if not self.env.user.share:
            articles_with_access = Article._get_internal_permission(filter_domain=['!', ('internal_permission', '=?', 'none')])
        member_permissions = Article._get_partner_member_permissions(self.env.user.partner_id)
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
    @api.depends('user_has_access', 'parent_id.user_has_access_parent_path')
    def _compute_user_has_access_parent_path(self):
        roots = self.filtered(lambda article: not article.parent_id)
        for article in roots:
            article.user_has_access_parent_path = article.user_has_access
        children = self - roots
        for article in children:
            ancestors = self.env['knowledge.article'].browse(article._get_ancestor_ids())
            article.user_has_access_parent_path = not any(not ancestor.user_has_access for ancestor in ancestors)

    @api.depends_context('uid')
    @api.depends('user_permission')
    def _compute_user_has_write_access(self):
        """ Compute if the current user has write access to the article based on
        permissions and memberships.

        Note that admins have all access through ACLs by default but fields are
        still using the permission-based computation. """
        for article in self:
            article.user_has_write_access = article.user_permission == 'write'

    def _search_user_has_write_access(self, operator, value):
        KnowledgeArticle = self.env["knowledge.article"]
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError("Unsupported search operator")

        # share is never allowed to write
        if self.env.user.share:
            if (value and operator == '=') or (not value and operator == '!='):
                return expression.FALSE_DOMAIN
            return expression.TRUE_DOMAIN

        articles_with_access = KnowledgeArticle._get_internal_permission(filter_domain=[('internal_permission', '=', 'write')])
        member_permissions = KnowledgeArticle._get_partner_member_permissions(self.env.user.partner_id)
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

    @api.depends_context('uid')
    @api.depends('user_has_access')
    def _compute_user_can_read(self):
        """ Compute read access, based on standard ACLs, which is either system
        group (which has access to everything), either based on members and
        permissions (see ``user_has_access``). Used mainly for views
        attributes or as a shortener for conditions. """
        if self.env.is_system():
            self.user_can_read = True
        else:
            readable = self.filtered_domain(self._get_read_domain())
            readable.user_can_read = True
            (self - readable).user_can_read = False

    @api.depends_context('uid')
    @api.depends('user_has_write_access')
    def _compute_user_can_write(self):
        """ Compute write access, based on standard ACLs, which is either system
        group (which has access to everything), either based on members and
        permissions (see ``user_has_write_access``). Used mainly for views
        attributes or as a shortener for conditions. """
        if self.env.is_system():
            self.user_can_write = True
        else:
            for article in self:
                article.user_can_write = article.user_has_write_access

    @api.depends('root_article_id.internal_permission', 'root_article_id.article_member_ids.permission')
    def _compute_category(self):
        # compute workspace articles
        workspace_articles = self.filtered(lambda a: a.root_article_id.internal_permission != 'none')
        workspace_articles.category = 'workspace'

        remaining_articles = self - workspace_articles
        if not remaining_articles:
            return

        results = self.env['knowledge.article.member']._read_group([
            ('article_id', 'in', remaining_articles.root_article_id.ids), ('permission', '!=', 'none')
        ], ['article_id'], ['__count'])  # each returned member is read on write.
        access_member_per_root_article = {article.id: count for article, count in results}

        for article in remaining_articles:
            # should never crash as non workspace articles always have at least one member with access.
            if access_member_per_root_article.get(article.root_article_id.id, 0) > 1:
                article.category = 'shared'
            else:
                article.category = 'private'

    @api.depends('favorite_ids')
    def _compute_favorite_count(self):
        favorites = self.env['knowledge.article.favorite']._read_group(
            [('article_id', 'in', self.ids)], ['article_id'], ['__count']
        )
        favorites_count_by_article = {article.id: count for article, count in favorites}
        for article in self:
            article.favorite_count = favorites_count_by_article.get(article.id, 0)

    @api.depends_context('uid')
    @api.depends('favorite_ids.user_id')
    def _compute_is_user_favorite(self):
        if self.env.user._is_public():
            self.is_user_favorite = False
            return
        favorites = self.env['knowledge.article.favorite'].search([
            ("article_id", "in", self.ids),
            ("user_id", "=", self.env.user.id),
        ])
        not_fav_articles = self - favorites.article_id
        fav_articles = self - not_fav_articles
        fav_sequence_by_article = {f.article_id.id: f.sequence for f in favorites}
        if not_fav_articles:
            not_fav_articles.is_user_favorite = False
            not_fav_articles.user_favorite_sequence = -1
        if fav_articles:
            fav_articles.is_user_favorite = True
        for fav_article in fav_articles:
            fav_article.user_favorite_sequence = fav_sequence_by_article[fav_article.id]

    def _search_is_user_favorite(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError("Unsupported search operation on favorite articles")

        if (value and operator == '=') or (not value and operator == '!='):
            return [('favorite_ids', 'in', self.env['knowledge.article.favorite'].sudo()._search(
                [('user_id', '=', self.env.uid)]
            ))]

        # easier than a not in on a 2many field (hint: use sudo because of
        # complicated ACL on favorite based on user access on article)
        return [('favorite_ids', 'not in', self.env['knowledge.article.favorite'].sudo()._search(
            [('user_id', '=', self.env.uid)]
        ))]

    @api.depends('is_article_visible_by_everyone', 'article_member_ids', 'root_article_id.article_member_ids')
    @api.depends_context('uid')
    def _compute_is_article_visible(self):
        """Compute if the user can see a specific article.
        The user can see it in two cases: when the article can be seen by everyone
        and when he is a member of the said article if it is visible only by its members.
        """
        visible_articles = self.filtered(lambda article: article.is_article_visible_by_everyone)
        visible_articles.is_article_visible = True
        if visible_articles == self:
            return

        member_only_articles = self - visible_articles
        results = self.env['knowledge.article.member']._read_group(
            domain=[('partner_id', '=', self.env.user.partner_id.id), ('permission', '!=', 'none')],
            groupby=['partner_id', 'article_id'],
        )

        pids_by_article = defaultdict(list)
        for partner, article in results:
            pids_by_article[article.id].append(partner.id)

        current_pid = self.env.user.partner_id.id
        for article in member_only_articles:
            article.is_article_visible = current_pid in (
                pids_by_article[article.id] + pids_by_article[article.root_article_id.id]
            )

    def _search_is_article_visible(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError(_("Unsupported search operation"))
        members_from_partner = self.env['knowledge.article.member']._search(
            [('partner_id', '=', self.env.user.partner_id.id)]
        )
        if (value and operator == '=') or (not value and operator == '!='):
            return [
                    '|',
                        ('is_article_visible_by_everyone', '=', True),
                        '|',
                            ('article_member_ids', 'in', members_from_partner),
                            ('root_article_id.article_member_ids', 'in', members_from_partner)
            ]

        return [
                '&',
                    ('is_article_visible_by_everyone', '=', False),
                    '&',
                        ('article_member_ids', 'not in', members_from_partner),
                        ('root_article_id.article_member_ids', 'not in', members_from_partner)
        ]

    @api.depends('root_article_id.is_article_visible_by_everyone')
    def _compute_is_article_visible_by_everyone(self):
        root_articles = self.filtered(lambda article: not article.parent_id)
        for article in (self - root_articles):
            article.is_article_visible_by_everyone = article.root_article_id.is_article_visible_by_everyone
        root_articles.is_article_visible_by_everyone = False # Forces initialization of the field if not already set.

    @api.depends('to_delete', 'write_date')
    def _compute_deletion_date(self):
        trashed_articles = self.filtered(lambda article: article.to_delete)
        (self - trashed_articles).deletion_date = False
        if trashed_articles:
            limit_days = self.env["ir.config_parameter"].sudo().get_param(
                "knowledge.knowledge_article_trash_limit_days"
            )
            try:
                limit_days = int(limit_days)
            except ValueError:
                limit_days = self.DEFAULT_ARTICLE_TRASH_LIMIT_DAYS
            for article in trashed_articles:
                article.deletion_date = article.write_date + timedelta(days=limit_days)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
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
        if not order or 'is_user_favorite' not in order:
            return super().search_fetch(domain, field_names, offset, limit, order)
        order_items = [order_item.strip().lower() for order_item in (order or self._order).split(',')]
        favorite_asc = any('is_user_favorite asc' in item for item in order_items)

        # Search articles that are favorite of the current user.
        my_articles_domain = expression.AND([[('favorite_ids.user_id', 'in', [self.env.uid])], domain])
        my_articles_order = ', '.join(item for item in order_items if 'is_user_favorite' not in item)
        articles_ids = super().search_fetch(my_articles_domain, field_names, order=my_articles_order).ids

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

        other_article_res = super().search_fetch(
            expression.AND([[('id', 'not in', my_articles_ids_skip)], domain]),
            field_names, article_offset, article_limit, article_order,
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
        if any(vals.get('is_template', False) for vals in vals_list) and not self.env.user.has_group('base.group_system'):
            raise ValidationError(_('You are not allowed to create a new template.'))

        defaults = self.default_get(['article_member_ids', 'internal_permission', 'parent_id'])
        vals_by_parent_id = {}
        vals_as_sudo = []
        parent_ids = set()

        for vals in vals_list:
            # Set body to match title if any, or prepare a void header to ease
            # article onboarding.
            if not vals.get('is_template', False) and "body" not in vals:
                vals["body"] = Markup('<h1>%s</h1>') % vals["name"] if vals.get("name") \
                               else Markup('<h1 class="oe-hint"><br></h1>')

            vals.update({
                'last_edition_date': fields.Datetime.now(),
                'last_edition_uid': self.env.user.id,
            })

            can_sudo = False
            # get values from vals or defaults
            member_ids = vals.get('article_member_ids') or defaults.get('article_member_ids') or False
            internal_permission = vals.get('internal_permission') or defaults.get('internal_permission') or False
            parent_id = vals.get('parent_id') or defaults.get('parent_id') or False
            if parent_id:
                parent_ids.add(parent_id)

            if not self.env.user._is_internal() and not self.env.su:
                if not parent_id and internal_permission != 'none':
                    raise AccessError(_('Only internal users are allowed to create workspace root articles.'))

                if internal_permission != 'none' and 'is_article_visible_by_everyone' in vals:
                    # do not let portal specify the visibility, it will inherit from the root article
                    del vals['is_article_visible_by_everyone']

            # force write permission for workspace articles
            if not parent_id and not internal_permission:
                vals.update({'internal_permission': 'write',
                             'parent_id': False,  # just be sure we don't grant privileges
                })

            # We need to check if the article creation needs to be done with sudo permissions and that
            # it is authorized.
            # This is authorized if :
            #   * The user is not the superuser
            #   * We do not try to create any favorite records or children articles in the same call
            #   * We do not try to create a child article
            #   * We want to create a single member that is the user creating the article

            # The reason why we would want to add the creator as a member for all articles is that
            # with the new visibility logic, when a user creates a new article in the workspace it is
            # set to only be visible to members.
            # This means that in order for him to see the article he just created, we add him to the
            # members, which needs sudo access.

            check_for_sudo = not self.env.su and \
                             not self.env.user._is_system() and \
                             not any(fname in vals for fname in ['favorite_ids', 'child_ids']) and \
                             not parent_id and member_ids and len(member_ids) == 1
            if check_for_sudo:
                self_member = member_ids[0][0] == Command.CREATE and \
                              member_ids[0][2].get('partner_id') == self.env.user.partner_id.id
                if self_member:
                    can_sudo = True

            # if no sequence, parent will have to be checked
            if not vals.get('sequence'):
                vals_by_parent_id.setdefault(parent_id, []).append(vals)
            vals_as_sudo.append(can_sudo)

        # check access to parents
        if parent_ids:
            try:
                self.check_access_rights('write')
                self.env['knowledge.article'].browse(list(parent_ids)).check_access_rule('write')
            except AccessError:
                raise AccessError(_("You cannot create an article under articles on which you cannot write"))

        # compute all maximum sequences / parent
        max_sequence_by_parent = {}
        if vals_by_parent_id:
            parent_ids = list(vals_by_parent_id.keys())
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
        if any(article.is_template \
            for article in self) and not self.env.user.has_group('base.group_system'):
            raise ValidationError(_('You are not allowed to update a template.'))
        if any(article.is_template != vals.get('is_template', False) \
            for article in self) and not self.env.user.has_group('base.group_system'):
            raise ValidationError(_('You are not allowed to update the type of a article or a template.'))

        # Move under a parent is considered as a write on it (permissions, ...)
        _resequence = False
        if not self.env.user._is_internal() and not self.env.su:
            writable_fields = self._get_portal_write_fields_allowlist()
            if all(article.category == 'private' for article in self):
                # let non internal users re-organize their private articles
                # and send them to trash if they wish
                writable_fields |= {'active', 'to_delete', 'parent_id'}

            if vals.keys() - writable_fields:
                raise AccessError(_('Only internal users are allowed to modify this information.'))

        if 'body' in vals:
            if len(self) == 1:
                handle_history_divergence(self, 'body', vals)
            vals.update({
                'last_edition_date': fields.Datetime.now(),
                'last_edition_uid': self.env.user.id,
            })
        else:
            vals.pop('last_edition_date', False)
            vals.pop('last_edition_uid', False)

        if 'parent_id' in vals:
            parent = self.env['knowledge.article']
            if vals.get('parent_id') and self.filtered(lambda r: r.parent_id.id != vals['parent_id']):
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
            self.sudo()._resequence()

        return result

    @api.ondelete(at_uninstall=False)
    def _check_template_deletion(self):
        if self.filtered('is_template') and not self.env.user.has_group('base.group_system'):
            raise ValidationError(_('You are not allowed to delete a template.'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if not default.get('name') and self.name:
            default['name'] = self.name if self.parent_id else _('%(article_name)s (copy)', article_name=self.name)
        return super().copy(default)

    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        """ Propagate the (copy) suffix addition to records created for children
        of copied articles, as those do not go through ``copy`` but the lower
        level ``copy_data`` instead. """
        if not default or 'name' not in default:
            if default is None:
                default = {}
            if self.name:
                default['name'] = self.name if self.parent_id else _('%(article_name)s (copy)', article_name=self.name)
        return super().copy_data(default=default)

    def copy_batch(self, default=None):
        """ Duplicates a recordset of articles. Filters out articles that are
        going to be duplicated during the duplication of their parent in order
        to prevent duplicating several times the same article. """
        current_ids = set(self.ids)
        # Remove records that will get duplicated with their parent
        to_copy = self.filtered(lambda article: not article._get_ancestor_ids() & current_ids)

        duplicates = self.create([
            article.with_context(active_test=False).copy_data(default=default)[0]
            for article in to_copy
        ])
        # update translations, skip name (hardcoded in default anyway) and o2m fields
        # as we don't need anything translated from them
        for old, new in zip(to_copy, duplicates):
            old.with_context(from_copy_translation=True).copy_translations(
                new,
                excluded=list(default.keys()) if default else [] + ['name', 'article_member_ids', 'favorite_ids']
            )

        return duplicates

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        if self.env.context.get('default_parent_id'):
            search_domain = expression.OR([[('parent_id', '=', self.env.context['default_parent_id'])], search_domain])
        stage_ids = stages._search(search_domain, order=order)
        return stages.browse(stage_ids)

    def _get_read_domain(self):
        """ Independently from admin bypass, give the domain allowing to read
        articles. """
        return [('user_has_access', '=', True)]

    @api.model
    def _get_portal_write_fields_allowlist(self):
        """" Fields that can be written on by a portal user. """
        return {'article_properties', 'article_properties_definition', 'body',
                'full_width', 'icon', 'is_article_item', 'is_locked', 'name',
                'sequence', 'stage_id'}

    # ------------------------------------------------------------
    # BASE MODEL METHODS
    # ------------------------------------------------------------

    @api.autovacuum
    def _gc_trashed_articles(self):
        limit_days = self.env["ir.config_parameter"].sudo().get_param(
            "knowledge.knowledge_article_trash_limit_days"
        )
        try:
            limit_days = int(limit_days)
        except ValueError:
            limit_days = self.DEFAULT_ARTICLE_TRASH_LIMIT_DAYS
        timeout_ago = datetime.utcnow() - timedelta(days=limit_days)
        domain = [("write_date", "<", timeout_ago), ("to_delete", "=", True)]
        return self.search(domain).unlink()

    def action_archive(self):
        return self._action_archive_articles()

    @api.model
    def name_create(self, name):
        """" This override is meant to make the 'name_create' symmetrical to the display_name.
        When creating an article, we attempt to extract a potential icon from the beginning of the
        name to correctly split the 'name' and 'icon' fields.

        This is especially important since some flows, such as importing records, are based on
        name_create to create missing records.
        It also allows pasting an article display_name into a m2o field and using the quick creation
        if it does not exist.

        Without this override, you would get '📄🚀 Article With Icon' (placeholder added as icon is
        not detected) instead of '🚀 Article With Icon' as result. """

        article_name, icon = self._extract_icon_from_name(name)
        if not icon:
            return super().name_create(name)

        record = self.create({
            'name': article_name,
            'icon': icon,
        })
        return record.id, record.display_name

    @api.depends('icon')
    def _compute_display_name(self):
        for rec in self:
            name = (rec.template_name if rec.is_template else rec.name) or _('Untitled')
            rec.display_name = f"{rec.icon or self._get_no_icon_placeholder()} {name}"

    def _get_no_icon_placeholder(self):
        """ Emoji used in templates as a placeholder when icon is False. It's
        here as a method because some lxml builds on macOS can not parse emoji
        characters, and a user using such a device would not be able to install
        the Knowledge module without an error.
        This method should be removed as soon as a solution is found allowing
        emojis to be parsed directly from a template on those devices.
        """
        return "📄"

    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """ This override is meant to make the 'name_search' symmetrical to the display_name.
        As we append the icon (emoji) before the article name, when searching based on that same
        syntax '[emoji] name' we need to return the appropriate results.

        This is especially important since some flows, such as exporting and re-importing records,
        are based on display_name / name_search to match records (for example when importing the article
        parent record, without this override it will never match). """

        if operator not in ('=', 'ilike'):
            return super()._name_search(name, domain, operator, limit, order)

        article_name, icon = self._extract_icon_from_name(name)
        if not icon:
            return super()._name_search(name, domain, operator, limit, order)

        domain = domain or []
        if icon == self._get_no_icon_placeholder():
            # special case using the icon placeholder (no icon stored but the display_name returns one)
            domain = expression.AND([domain, [
                ('name', operator, article_name),
                '|',
                ('icon', '=', icon),
                ('icon', '=', False),
            ]])
        else:
            domain = expression.AND([domain, [
                ('name', operator, article_name),
                ('icon', '=', icon),
            ]])

        return self._search(domain, limit=limit, order=order)

    def _get_common_copied_data(self):
        return {
            "article_properties_definition": self.article_properties_definition,
            "body": self.body,
            "cover_image_id": self.cover_image_id.id,
            "cover_image_position": self.cover_image_position,
            "full_width": self.full_width,
            "icon": self.icon,
            "is_desynchronized": False,
            "is_locked": False,
            "name": _("%(article_name)s (copy)", article_name=self.name) if self.name else False,
        }

    def _update_article_references(self, original_article):
        """
        Updates the IDs stored in the body of the current articles.
        After calling that method, the embedded views listing the article items
        of the original article will now list the article items of the current record.
        :param <knowledge.article> original_article: original article
        """
        for article in self:
            if is_html_empty(article.body):
                continue
            needs_embed_view_update = False
            fragment = html.fragment_fromstring(article.body, create_parent=True)
            for element in fragment.findall(".//*[@data-behavior-props]"):
                if "o_knowledge_behavior_type_embedded_view" in element.get("class"):
                    behavior_props = json.loads(parse.unquote(element.get("data-behavior-props")))
                    context = behavior_props.get("context", {})
                    if context.get("default_is_article_item") and context.get("active_id") == original_article.id:
                        context.update({
                            "active_id": article.id,
                            "default_parent_id": article.id
                        })
                        element.set("data-behavior-props", parse.quote(json.dumps(behavior_props), safe="()*!'"))
                        needs_embed_view_update = True

            if needs_embed_view_update:
                article.write({
                    "body": html.tostring(fragment, encoding="unicode")
                })

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    @api.returns('self', lambda value: value.id)
    def action_make_private_copy(self):
        """ Creates a copy of an article. != duplicate article (see `copy`).
        Creates a new private article with the same body, icon and cover,
        but drops other fields such as members, childs, permissions etc.
        Note: Article references will be update, see `_update_article_references`
        """
        self.ensure_one()
        article_vals = self._get_common_copied_data()
        article_vals.update({
            "article_member_ids": [(0, 0, {
                "partner_id": self.env.user.partner_id.id,
                "permission": 'write'
            })],
            "internal_permission": "none",
            "parent_id": False,
        })
        article = self.create(article_vals)
        article._update_article_references(self)
        # Copy the related stages for the /kanban command:
        for stage in self.env["knowledge.article.stage"].search([("parent_id", "=", self.id)]):
            stage.copy({
                "parent_id": article.id
            })
        return article

    @api.returns('self', lambda value: value.id)
    def action_clone(self):
        """Creates a duplicate of an article in the same context as the original.
        This means that this methods create a copy with the same parent,
        permission and properties as the original
        Note: Article references will be update, see `_update_article_references`
        """
        self.ensure_one()
        if not self.user_can_write or not (self.parent_id and self.parent_id.user_can_write):
            return self.action_make_private_copy()
        article_vals = self._get_common_copied_data()
        article_vals.update({
            "internal_permission": self.internal_permission,
            "parent_id": self.parent_id.id,
            "article_properties": self.article_properties,
            "is_article_item": self.is_article_item,
        })
        article = self.create(article_vals)
        article._update_article_references(self)
        # Copy the related stages for the /kanban command:
        for stage in self.env["knowledge.article.stage"].search([("parent_id", "=", self.id)]):
            stage.copy({
                "parent_id": article.id
            })
        return article

    def action_home_page(self):
        """ Redirect to the home page of knowledge, which displays an article.
        Chosen articles comes from

          * either self if it is not void (taking the first article);
          * ``res_id`` key from context;
          * find the first accessible article, based on favorites and sequence
            (see ``_get_first_accessible_article``);
        """
        article = self[0] if self else False
        if not article and self.env.context.get('res_id', False):
            article = self.browse([self.env.context["res_id"]])
            if not article.exists():
                raise UserError(_("The Article you are trying to access has been deleted"))
        if not article:
            article = self._get_first_accessible_article()

        action = self.env['ir.actions.act_window']._for_xml_id('knowledge.knowledge_article_action_form')
        action['res_id'] = article.id
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

        # need to sudo to be able to write on the article model even with read access
        to_favorite_sudo = self.sudo().filtered(lambda article: not article.is_user_favorite)
        to_unfavorite = self - to_favorite_sudo
        to_favorite_sudo.write({'favorite_ids': [(0, 0, {'user_id': self.env.user.id})]})
        if to_unfavorite:
            self.env['knowledge.article.favorite'].sudo().search([
                ('article_id', 'in', to_unfavorite.ids), ('user_id', '=', self.env.user.id)
            ]).unlink()
        # manually invalidate cache to recompute the favorites related fields
        self.invalidate_recordset(fnames=["is_user_favorite", "favorite_ids"])
        return self[0].is_user_favorite if self else False

    def action_article_archive(self):
        self.action_archive()
        return self.env["knowledge.article"].action_home_page()

    def action_send_to_trash(self):
        action_home_page = self._action_archive_articles(send_to_trash=True)
        # no need to reload when inside the tree view
        if self.env.context.get('in_tree_view'):
            return False
        return action_home_page
    def _action_archive_articles(self, send_to_trash=False):
        """ When archiving
                  * archive the current article and all its writable descendants;
                  * unreachable descendants (none, read) are set as free articles without
                    root;
        :param bool send_to_trash: Article specific archive:
            after archive, redirect to the home page displaying accessible
            articles, instead of doing nothing.
        """
        # _detach_unwritable_descendants calls _filter_access_rules_python which returns
        # a sudo-ed recordset
        writable_descendants = self._detach_unwritable_descendants().with_env(self.env)
        (self + writable_descendants).filtered('active').toggle_active()
        if send_to_trash:
            (self + writable_descendants).to_delete = True
            (self + writable_descendants)._send_trash_notifications()
            return self.env['knowledge.article'].with_context(res_id=False).action_home_page()
        return True

    def action_unarchive_article(self):
        """ Called by the archive action from the form view action menu.
        """
        self.ensure_one()
        self.action_unarchive()

    def action_unarchive(self):
        """ When unarchiving

          * unarchive the current article and all its writable descendants;
          * unreachable descendants (none, read) are set as free articles without
            root; Side note: the main use case that we support is to be able to
            undo an archive by mistake. So the unarchiving should unarchive all
            the article archived by the user. If, in some other cases, there are
            unreachable descendant for the current user, some of the original
            archived articles won't be restored.
          * To avoid 'restoring' an article that will not appear anywhere on
            the knowledge home page, make the article a root article.
        """
        for article_item in self.filtered(lambda article: article.is_article_item \
                                        and article.parent_id not in self \
                                        and article.parent_id.sudo().to_delete):
            raise UserError(
                _('"%(article_item_name)s" is an Article Item from "%(article_name)s" and cannot be restored on its own. Contact the owner of "%(article_name)s" to have it restored instead.',
                    article_item_name=article_item.display_name,
                    article_name=article_item.parent_id.display_name))

        writable_descendants = self.with_context(active_test=False)._detach_unwritable_descendants().with_env(self.env)
        res = super(Article, self + writable_descendants).action_unarchive()
        # Trash management: unarchive removes the article from the trash
        articles_to_restore = (self + writable_descendants).filtered(lambda article: article.to_delete)
        articles_to_restore.write({'to_delete': False})
        for article_sudo in self.sudo().filtered(lambda article: article.parent_id.to_delete):
            write_values = article_sudo._desync_access_from_parents_values()
            # Make it root
            write_values.update({
                'parent_id': False,
                'is_desynchronized': False
            })
            article_sudo.write(write_values)
        return res

    def action_join(self):
        self.ensure_one()
        current_user = self.env.user
        if current_user.share or not self.user_has_access or not self.user_has_access_parent_path:
            raise AccessError(
                _("You need to have access to this article in order to join its members.") if not self.parent_id else
                _("You need to have access to this article's root in order to join its members.")
            )
        if self.parent_id:
            self.root_article_id.sudo()._add_members(current_user.partner_id, self.root_article_id.internal_permission)
            return self.action_home_page()
        else:
            self.sudo()._add_members(current_user.partner_id, self.internal_permission)
            return False

    # ------------------------------------------------------------
    # SEQUENCE / ORDERING
    # ------------------------------------------------------------

    def move_to(self, parent_id=False, before_article_id=False, category=False):
        """ Move an article in the tree.

        :param int parent_id: id of an article that will be the new parent;
        :param int before_article_id: id of an article before which the article
          should be moved. Otherwise it is put as last parent children;
        :param str category: target category ('workspace', 'private', 'shared')
          can be omitted if the destination can be deduced from parent_id or
          before_article_id;

        :return: True
        """
        self.ensure_one()
        before_article = self.env['knowledge.article'].browse(before_article_id) if before_article_id else self.env['knowledge.article']
        parent = self.env['knowledge.article'].browse(parent_id) if parent_id else self.env['knowledge.article']
        # deduce category if not specified
        category = category or parent.category or before_article.category
        if not category:
            raise ValidationError(
                _("The destination placement of %(article_name)s is ambiguous, you should specify the category.",
                  article_name=self.display_name)
            )
        if category == 'shared' and not parent and (self.parent_id or self.category != 'shared'):
            raise ValidationError(
                _("Cannot move %(article_name)s as a root of the 'shared' section since access rights can not be inferred without a parent.",
                  article_name=self.display_name)
            )
        if parent.is_article_item:
            raise ValidationError(
                _("You can't move %(article_name)s under %(item_name)s, as %(item_name)s is an Article Item. "
                  "Convert %(item_name)s into an Article first.", article_name=self.display_name, item_name=parent.display_name)
            )

        if category == 'private':
            # making an article private requires a lot of extra-processing, use specific method
            return self._move_and_make_private(parent=parent, before_article=before_article)

        values = {'parent_id': parent_id}
        if before_article:
            values['sequence'] = before_article.sequence
        if parent_id and not self.parent_id:
            # be sure to reset internal permission when moving a root article under a parent
            values['internal_permission'] = False
        if not parent_id and category == 'workspace':
            # be sure to have an internal permission on the article if moved outside
            # of an hierarchy
            values.update({
                'internal_permission': 'write',
                'is_desynchronized': False
            })

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
        if parent_ids:
            domain = [('parent_id', 'in', parent_ids)]
        else:
            domain = [('parent_id', '=', False)]
        rg_results = self.env['knowledge.article'].sudo()._read_group(
            domain,
            ['parent_id'],
            ['sequence:max']
        )
        return {parent.id: sequence_max for parent, sequence_max in rg_results}

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    @api.model
    @api.returns('knowledge.article', lambda article: article.id)
    def article_create(self, title=False, parent_id=False, is_private=False, is_article_item=False, article_properties=False):
        """ Helper to create articles, allowing to pre-compute some configuration
        values.

        :param str title: name of the article;
        :param int parent_id: id of an existing article who will be the parent
          of the newly created articled. Must be writable;
        :param bool is_private: set current user as sole owner of the new article;
        :param bool is_article_item: set the created article as an article item;
        """
        parent = self.browse(parent_id) if parent_id else self.env['knowledge.article']
        values = {
            'is_article_item': is_article_item,
            'parent_id': parent.id
        }
        if title:
            values['name'] = title

        if parent:
            if not is_private and parent.category == "private":
                is_private = True
        else:
            # child do not have to setup an internal permission as it is inherited
            values['internal_permission'] = 'none' if is_private else 'write'
            # For private articles, we need to set a member because the internal_permission is set to
            # 'none' which restricts the access to only members of the article.

            # For workspace articles, we need to add a member because the visibility of a brand new root
            # article is always set to 'Members', meaning that only the members are able to see it at all times in
            # their tree.
            # And we need the creator to be able to see it in order for him to easily edit it later.
            values['article_member_ids'] = [(0, 0, {
                'partner_id': self.env.user.partner_id.id,
                'permission': 'write',
            })]

        if is_private:
            if parent and parent.category != "private":
                raise ValidationError(
                    _("Cannot create an article under article %(parent_name)s which is a non-private parent",
                      parent_name=parent.display_name)
                )

        if is_article_item and article_properties:
            values['article_properties'] = article_properties

        return self.create(values)

    def get_user_sorted_articles(self, search_query, limit=40, hidden_mode=False):
        """ Called when using the Command palette to search for articles matching the search_query.
        As the article should be sorted also in function of the current user's favorite sequence, a search_read rpc
        won't be enough to returns the articles in the correct order.
        This method returns a list of article proposal matching the search_query sorted by:
            - name = query & is_user_favorite - by Favorite sequence
            - name = query & Favorite count
            - root.name = query & is_user_favorite - by Favorite sequence
            - root.name = query & Favorite count
        and returned result mimic a search_read result structure.

        The parameter hidden_mode separates the search into 2 modes: visible and hidden.
        When hidden_mode is True, we search for articles that are hidden, hence that have
        is_article_visible at False.
        When hidden_mode is False, we search for articles that are visible, hence that have
        is_article_visible at True.

        This means that we need to add in the search_domain the leaf ('is_article_visible', '!=', hidden_mode)
        since the value of is_article_visible is the opposite of hidden_mode.
        """
        search_domain = [
            ("is_template", "=", False),
            ("is_article_visible", "!=", hidden_mode),
            ("user_has_access", "=", True),  # Admins won't see other's private articles.
        ]
        if search_query:
            search_domain = expression.AND([search_domain, [
                "|",
                    ("name", "ilike", search_query),
                    ("root_article_id.name", "ilike", search_query),
            ]])

        articles_query = self._search(search_domain)
        self.env.cr.execute(SQL('''
       SELECT knowledge_article.id,
              knowledge_article.name,
              COALESCE(CAST(fav.id AS BOOLEAN), FALSE) AS is_user_favorite,
              knowledge_article.favorite_count,
              knowledge_article.root_article_id,
              root_article.icon AS root_article_icon,
              root_article.name AS root_article_name,
              knowledge_article.icon
         FROM knowledge_article
    LEFT JOIN knowledge_article_favorite AS fav
           ON knowledge_article.id = fav.article_id AND fav.user_id = %s
    LEFT JOIN knowledge_article AS root_article
           ON knowledge_article.root_article_id = root_article.id
        WHERE %s
     ORDER BY CASE
                  WHEN knowledge_article.name IS NOT NULL THEN
                      POSITION(LOWER(%s) IN LOWER(knowledge_article.name)) > 0
                  ELSE
                      FALSE
              END DESC,
              CASE
                  WHEN %s THEN
                      NOT COALESCE(CAST(knowledge_article.parent_id AS BOOLEAN), FALSE)
                  ELSE
                      FALSE
              END DESC,
              is_user_favorite DESC,
              COALESCE(fav.sequence, -1),
              knowledge_article.favorite_count DESC,
              knowledge_article.write_date DESC,
              knowledge_article.id DESC
           %s
            ''',
            self.env.user.id,
            articles_query.where_clause,
            search_query,
            hidden_mode,
            SQL("LIMIT %s", limit) if limit else SQL()
        ))
        sorted_articles = self.env.cr.dictfetchall()
        # Create a tuple with the id and name_get for root_article_id to
        # mimic the result of a read.
        for sorted_article in sorted_articles:
            # Get the display name of the root article using the same logic as
            # in name_get.
            sorted_article['root_article_id'] = (
                sorted_article['root_article_id'],
                "%s %s" % (
                    sorted_article['root_article_icon'] or self._get_no_icon_placeholder(),
                    sorted_article['root_article_name']
                )
            )
            del sorted_article['root_article_icon']
            del sorted_article['root_article_name']
        return sorted_articles

    # ------------------------------------------------------------
    # PERMISSIONS / MEMBERS MANAGEMENT
    # ------------------------------------------------------------

    def restore_article_access(self):
        """ Resets permissions based on ancestors. It removes all members except
        members on the articles that are not on any ancestor or that have higher
        permission than from ancestors.

        Security note: this method checks for write access on current article,
        considering it as sufficient to restore access and members.
        (side-note: portal users cannot alter article access)
        """
        self.ensure_one()
        if not self.parent_id:
            return False
        if not self.env.su and not self.user_can_write:
            raise AccessError(
                _('You have to be editor on %(article_name)s to restore it.',
                  article_name=self.display_name))
        if not self.env.su and not self.env.user._is_internal():
            raise _('Only internal users are allowed to restore the original article access information.')

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

    def invite_members(self, partners, permission, message=None):
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

            members_command = self._add_members_command(partners, permission)
            self.sudo().write({'article_member_ids': members_command})
            self._send_invite_mail(partners, permission, message)

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
            # desync is done as sudo, explicitly check access
            if not self.env.su and not self.user_can_write:
                raise AccessError(
                    _('You have to be editor on %(article_name)s to change its internal permission.',
                      article_name=self.display_name))
            # sudo to write on members
            return self.sudo().write(
                self._desync_access_from_parents_values(
                    force_internal_permission=permission
                )
            )

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

        Security notes:
        - this method checks for write access on current article,
          considering it as sufficient to modify members permissions.
        - portal users cannot alter memberships in any way.

        :param <knowledge.article.member> member: member whose permission
          is to be updated. Can be a member of 'self' or one of its ancestors;
        :param str permission: new permission, one of 'none', 'read' or 'write';
        :param bool is_based_on: whether rights are inherited or through membership;
        """
        self.ensure_one()
        if not self.env.su and not self.user_can_write:
            raise AccessError(
                _('You have to be editor on %(article_name)s to modify members permissions.',
                  article_name=self.display_name))
        elif not self.env.su and not self.env.user._is_internal():
            raise AccessError(_("Only internal users are allowed to alter memberships."))

        if is_based_on:
            downgrade = ARTICLE_PERMISSION_LEVEL[member.permission] > ARTICLE_PERMISSION_LEVEL[permission]
            if downgrade:
                # sudo to write on members
                self.sudo().write(
                    self._desync_access_from_parents_values(
                        force_partners=member.partner_id,
                        force_member_permission=permission
                    )
                )
            else:
                self._add_members(member.partner_id, permission)
        else:
            member.article_id.sudo().with_context(knowledge_member_skip_writable_check=True).write({
                'article_member_ids': [(1, member.id, {'permission': permission})]
            })

    def set_is_article_visible_by_everyone(self, is_article_visible_by_everyone):
        """Set the visibility of an article to the provided value.
        If the new value is False, we need to check if the user is a member of the article.
        If that's not the case then we add it as a member of the article with the same permission as the
        article.
        This ensures that the user can see the article when modifying its visibility."""
        self.ensure_one()
        self.write({'is_article_visible_by_everyone': is_article_visible_by_everyone})

        if (not is_article_visible_by_everyone) and not self.env.user.partner_id in self.article_member_ids.partner_id:
            self._add_members(self.env.user.partner_id, self.internal_permission)

    def _remove_member(self, member):
        """ Removes a member from the article. If the member was based on a
        parent article, the current article will be desynchronized form its parent.
        We also ensure the partner to remove is removed after the desynchronization
        if was copied from parent.
        If the user remove its own member on a private article, the article is
        archived instead.

        Security note
          * portal users cannot alter article membership
          * when removing themselves: users need only read access on the article
            (automatically checked by access on self);
          * when removing someone else: write access is required on the article
            (explicitly checked);

        :param <knowledge.article.member> member: member to remove
        """
        self.ensure_one()
        if not member:
            raise ValueError(_('Trying to remove wrong member.'))

        if not self.env.su and not self.env.user._is_internal():
            raise AccessError(_("Only internal users are allowed to remove memberships."))

        # belongs to current article members
        current_membership = self.article_member_ids.filtered(lambda m: m == member)

        # Archive private article if remove self member.
        remove_self = member.partner_id == self.env.user.partner_id
        if remove_self and self.category == 'private' and current_membership:
            return self.action_archive()

        # If user doesn't gain higher access when removing own member,
        # we should allow to do it.
        self_escalation = not (remove_self and \
                             ARTICLE_PERMISSION_LEVEL[member.permission] > ARTICLE_PERMISSION_LEVEL[self.inherited_permission])
        if not self.env.su and self_escalation and not self.user_can_write:
            raise AccessError(
                _("You have to be editor on %(article_name)s to remove or exclude member %(member_name)s.",
                  article_name=self.display_name,
                  member_name=member.display_name))
        # member is on current article: remove member
        if current_membership:
            self.sudo().write({'article_member_ids': [(2, current_membership.id)]})
        # inherited rights from parent: desync and remove member
        else:
            self.sudo().write(
                self._desync_access_from_parents_values(
                    force_partners=self.article_member_ids.partner_id
                )
            )
            current_membership = self.article_member_ids.filtered(lambda m: m.partner_id == member.partner_id)
            if current_membership:
                self.sudo().write({'article_member_ids': [(2, current_membership.id)]})

    def _add_members(self, partners, permission, force_update=True):
        """ Adds new members to the current article with the given permission.
        If a given partner is already member permission is updated instead.

        Security note: this method checks for write access on current article,
        considering it as sufficient to add new members.
        (side-note: portal users can't alter memberships, see '_add_members_command')

        :param <res.partner> partners: recordset of res.partner for which
          new members are added;
        :param string permission: member permission, one of 'none', 'read' or 'write';
        :param boolean force_update: if already existing, force the new permission;
          this can be used to create default members and left existing one untouched;
        """
        self.ensure_one()
        members_command = self._add_members_command(
            partners, permission, force_update=force_update
        )
        return self.sudo().write({'article_member_ids': members_command})

    def _add_members_command(self, partners, permission, force_update=True):
        """ Implementation of ``_add_members``, returning commands to update
        the article. Used when caller prefers commands compared to updating
        directly the article.

        Note that portal users cannot alter memberships in any way.

        See main method for more details. """
        self.ensure_one()
        if not self.env.su and not self.user_can_write:
            raise AccessError(
                _("You have to be editor on %(article_name)s to add members.",
                  article_name=self.display_name))
        if not self.env.su and not self.env.user._is_internal():
            raise AccessError(_("Only internal users are allowed to alter memberships."))

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
        return members_command

    def _desync_access_from_parents_values(self, force_internal_permission=False,
                                           force_partners=False, force_member_permission=False):
        """ Get the necessary values to copy all inherited accesses from parents
        on the article and desynchronize the article from its parent,
        allowing custom access management. We allow to force permission of
        given partners.

        :param string force_internal_permission: force a new internal permission
          for the article. Otherwise fallback on inherited computed internal
          permission;
        :param <res.partner> force_partners: force permission of new members
          related to those partners;
        :param string force_member_permission: used with force_partners to
          specify the custom permission to give. One of 'none', 'read', 'write';
        """
        self.ensure_one()
        new_internal_permission = force_internal_permission or self.inherited_permission
        members_commands = self._copy_access_from_parents_commands(
            force_partners=force_partners,
            force_member_permission=force_member_permission
        )

        return {
            'article_member_ids': members_commands,
            'internal_permission': new_internal_permission,
            'is_desynchronized': True,
        }

    def _copy_access_from_parents_commands(self, force_partners=False, force_member_permission=False):
        """ Prepares commands for all inherited accesses from parents on the given
        article. It allows to de-synchronize the article from its parent and
        allows custom access management. We allow to force permission of given
        partners, bypassing inherited ones.

        :param <res.partner> force_partners: force permission of new members
          related to those partners;
        :param str force_member_permission: force a new permission to partners
          given by force_partners. Otherwise fallback on inherited computed
          internal permission;

        :return list member_commands: commands to be applied on 'article_member_ids'
          field;
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

    def _detach_unwritable_descendants(self):
        """ When taking specific actions on an article like archiving or making
        it private, we want to be able to 'detach' the unaccessible children and
        set them as free (root) articles. Indeed in those business flows you
        should not change the current access level of children articles.

        This method takes care of correctly detaching those children and returns
        a subset of children to which the user effectively has write access to.

        As the children are moved to "root" articles we also reset their desync
        status. Indeed, a root article cannot be desyncronized as stated by SQL
        constraints.

        Note: this might produce funny results when involving a hierarchy with
        invisible nodes in it (A-B-C where B is not achievable). You might
        archive / privatize articles and break hierarchy without knowing it.

        Security note: this method does not check accesses. Caller has to ensure
        access is granted, depending on the business flow.

        :return <knowledge.article> children: the children articles which were
          not detached, meaning that current user has write access on them """
        all_descendants_sudo = self.sudo()._get_descendants()
        writable_descendants_sudo = all_descendants_sudo.with_env(self.env)._filter_access_rules_python('write')
        other_descendants_sudo = all_descendants_sudo - writable_descendants_sudo

        # copy rights to allow breaking the hierarchy while keeping access for members
        # do this on synchronized articles as desynchronized one do not inherit from parent
        for article_sudo in other_descendants_sudo.filtered(lambda article: not article.is_desynchronized):
            article_sudo.write({
                'article_member_ids': article_sudo._copy_access_from_parents_commands()
            })

        # create new root articles and reset desync: direct children of these articles +
        # the writable descendants. Indeed they are going to be modified the same way
        # as "self" (archived / moved to private) -> all their children should be detached
        new_roots_woperm_sudo = other_descendants_sudo.filtered(
            lambda article: article.parent_id in (self + writable_descendants_sudo) and not article.internal_permission)
        new_roots_wperm_sudo = other_descendants_sudo.filtered(
            lambda article: article.parent_id in (self + writable_descendants_sudo) and article.internal_permission)
        if new_roots_wperm_sudo:
            new_roots_wperm_sudo.write({
                'is_desynchronized': False,
                'parent_id': False
            })
        for new_root_sudo in new_roots_woperm_sudo:
            new_root_sudo.write({
                'is_desynchronized': False,
                'internal_permission': new_root_sudo.inherited_permission,
                'parent_id': False,
            })

        return writable_descendants_sudo

    def _move_and_make_private(self, parent=False, before_article=False):
        """ Set as private: remove members, ensure current user is the only member
        with write access. Requires a sudo to bypass member ACLs after checking
        write access on the article.

        Children articles to which the user also has a write access to are made
        private as well. Other articles are detached, see '_detach_unwritable_descendants'
        for details.

        :param <knowledge.article> parent: an optional parent to move the article under;
        :param <knowledge.article> before_article: article before which the article
          should be moved. Otherwise it is put as last parent children;

        :return: True
        """
        self.ensure_one()
        parent = parent if parent is not False else self.env['knowledge.article']
        before_article = before_article if before_article is not False else self.env['knowledge.article']

        try:
            self.check_access_rights('write')
            (self + parent).check_access_rule('write')
        except (AccessError, UserError):
            if parent:
                raise AccessError(
                    _("You are not allowed to move '%(article_name)s' under '%(parent_name)s'.",
                      article_name=self.display_name,
                      parent_name=parent.display_name)
                )
            raise AccessError(
                _("You are not allowed to make '%(article_name)s' private.", article_name=self.display_name)
            )

        # first detach unwritable children (see ``_detach_unwritable_descendants``)
        writable_descendants_sudo = self._detach_unwritable_descendants()

        article_values = {
            # reset internal permission if parent is set (will inherit) or force private (aka 'none')
            'internal_permission': False if parent else 'none',
            # cannot be desync when made private as we wipe members access
            'is_desynchronized': False,
            'parent_id': parent.id if parent else False,
        }
        if before_article:
            article_values['sequence'] = before_article.sequence

        self_sudo = self.sudo()
        # remove members as the article is moved to private
        members_to_remove = self_sudo.article_member_ids
        self_member_command = []
        if not parent:
            # make sure the current user is the only member left with write access to the article
            # if we have a parent, this is not necessary as we will inherit members access from them
            self_member = self_sudo.article_member_ids.filtered(lambda m: m.partner_id == self.env.user.partner_id)
            if self_member:
                self_member_command = [(1, self_member.id, {'permission': 'write'})]
                # keep current member
                members_to_remove = members_to_remove.filtered(
                    lambda member: member.partner_id != self.env.user.partner_id
                )
            else:
                self_member_command = [(0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                })]

        article_values['article_member_ids'] = [
            (2, member.id)
            for member in members_to_remove
        ] + self_member_command

        res = self_sudo.with_context(knowledge_member_skip_writable_check=True).write(article_values)

        # remove all specific memberships configurations on children. They now inherit
        # the only 'write' member from their parent now, making them private.
        writable_descendants_sudo.with_context(knowledge_member_skip_writable_check=True).write({
            'internal_permission': False,
            'article_member_ids': [(5, 0)],
        })

        return res

    def _has_write_member(self, partners_to_exclude=False, members_to_exclude=False):
        """ Method allowing to check if this article still has at least one member
        with write access. Typically used during constraints checks.

        Please note that this method is *not* optimized and should be avoided by
        using ``_get_article_member_permissions`` instead when possible.

        :param <res.partner> partners_to_exclude: used when checking recursively
          through article parents, we only check for the most specific access
          for a given partner;
        :param <knowledge.article.member> members_to_exclude: memberships that
          should not be considered when checking for a write access, used when
          unlinking members that should not be taken into account;

        :return boolean: whether a write member has been found;
        """
        self.ensure_one()
        partners_to_exclude = partners_to_exclude if partners_to_exclude else self.env['res.partner']

        article_members = self.article_member_ids
        if members_to_exclude:
            article_members -= members_to_exclude

        if any(m.permission == 'write' and m.partner_id not in partners_to_exclude
               for m in article_members):
            return True
        if not self.is_desynchronized and self.parent_id:
            return self.parent_id._has_write_member(
                partners_to_exclude=article_members.partner_id | partners_to_exclude
            )
        return False

    # ------------------------------------------------------------
    # PERMISSIONS BATCH COMPUTATION
    # ------------------------------------------------------------

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
        additional_fields = additional_fields or {}
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
            SELECT a.id, a.parent_id, a.is_desynchronized, m.id as member_id,
                   m.partner_id, m.permission
              FROM knowledge_article a
         LEFT JOIN knowledge_article_member m
                ON a.id = m.article_id
        ), article_rec as (
            SELECT perms1.id, perms1.id as article_id, perms1.parent_id,
                   perms1.member_id, perms1.partner_id, perms1.permission,
                   perms1.id as origin_id, 0 as level,
                   perms1.is_desynchronized
              FROM article_perms as perms1
             UNION
            SELECT perms2.id, perms_rec.article_id, perms2.parent_id,
                   perms2.member_id, perms2.partner_id, perms2.permission,
                   perms2.id as origin_id, perms_rec.level + 1,
                   perms2.is_desynchronized
              FROM article_perms as perms2
        INNER JOIN article_rec perms_rec
                ON perms_rec.parent_id=perms2.id
                   AND perms_rec.is_desynchronized is not true
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

                # update our resulting dict based on additional fields
                article_members[article_id][partner_id].update({
                    field_alias: result[field_alias] if model != 'knowledge.article' or origin_id != article_id else False
                    for model, fields_list in additional_fields.items()
                    for (field, field_alias) in fields_list
                })
        # add empty member for each article that doesn't have any.
        empty_member = {
            'based_on': False, 'member_id': False, 'permission': None,
            **{
                field_alias: False
                for model, fields_list in additional_fields.items()
                for field, field_alias in fields_list
            }}
        for article in self.filtered(lambda a: a.id not in article_members):
            article_members[article.id][None] = empty_member
        return article_members

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _mail_track(self, tracked_fields, initial_values):
        changes, tracking_value_ids = super()._mail_track(tracked_fields, initial_values)
        if {'parent_id', 'root_article_id'} & changes and not self.user_has_write_access:
            partner_name = self.env.user.partner_id.display_name
            message_body = _("Logging changes from %(partner_name)s without write access on article %(article_name)s due to hierarchy tree update",
                partner_name=partner_name, article_name=self.display_name)
            self._track_set_log_message(Markup("<p>%s</p>") % message_body)
        return changes, tracking_value_ids

    def _send_invite_mail(self, partners, permission, message=None):
        self.ensure_one()

        partner_to_bodies = {}
        for partner in partners:
            partner_to_bodies[partner] = self.env['ir.qweb'].with_context(lang=partner.lang)._render(
                'knowledge.knowledge_article_mail_invite',
                {
                    'record': self,
                    'user': self.env.user,
                    'permission': permission,
                    'message': message,
                }
            )

        if self.display_name:
            subject = _('Article shared with you: %s', self.display_name)
        else:
            subject = _('Invitation to access an article')

        if permission == 'read':
            permission_label = _('Read')
        else:
            permission_label = _('Write')

        for partner, body in partner_to_bodies.items():
            self.with_context(lang=partner.lang).message_notify(
                body=body,
                email_layout_xmlid='mail.mail_notification_layout',
                partner_ids=partner.ids,
                subject=subject,
                subtitles=[self.display_name, _('Your Access: %s', permission_label)],
            )

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)
        if not self or not msg_vals.get('partner_ids'):
            return groups
        new_group = []
        for member in self.article_member_ids.filtered(
            lambda member: member.partner_id.id in msg_vals['partner_ids'] and member.partner_id.partner_share
        ):
            url = url_join(
                self.get_base_url(),
                f"/knowledge/article/invite/{member.id}/{member._get_invitation_hash()}"
            )
            new_group.append(
                (f'group_knowledge_member_{member.id}', lambda pdata: pdata['id'] == member.partner_id.id, {
                    'has_button_access': True,
                    'button_access': {
                        'url': url,
                    },
                })
            )
        return new_group + groups

    def _send_trash_notifications(self):
        """ This method searches all the partners that should be notified about
        articles have been trashed. As each partner to notify may have different
        accessible articles depending on their rights, for each partner, we need
        to retrieve the first accessible article that will be considered for
        them as the root trashed article. A notification is sent to each partner
        to notify with the list of their own accessible articles."""
        partners_to_notify = self.article_member_ids.filtered(
            lambda member: member.permission in ['read', 'write']
        ).partner_id

        KnowledgeArticle = self.env["knowledge.article"].with_context(active_test=False, allowed_company_ids=[])
        sent_messages = self.env['mail.message']
        for partner in partners_to_notify.filtered(lambda p: not p.partner_share):
            # if only one article, all the partner_to_notify have access to the article.
            if len(self) == 1:
                main_articles, children = self, KnowledgeArticle
            else:
                # Current partner may have no access to some of the articles_to_notify.
                # Get all accessible articles for the current partner
                partner_user = partner.user_ids.filtered(lambda u: not u.share)[0]
                accessible_articles = KnowledgeArticle.with_user(partner_user).search(
                    [('id', 'in', self.ids)]
                )

                # "Main articles" are articles that:
                #   - has no parent
                #   - OR the current partner as no access to their parent
                #   - OR the parent article can be accessed but is not archived.
                main_articles = accessible_articles.sudo().filtered(
                    lambda a: a.parent_id not in accessible_articles
                )
                children = accessible_articles - main_articles

            # Set the partner lang in context to send mail in partner lang.
            partner_lang = get_lang(self.env, lang_code=partner.lang).code
            self = self.with_context(lang=partner_lang)  # force translation of subject

            if len(main_articles) == 1:
                subject = _("%s has been sent to Trash", main_articles.name or _("Untitled"))
            else:
                subject = _("Some articles have been sent to Trash")

            body = self.env['ir.qweb'].with_context(lang=partner_lang)._render(
                'knowledge.knowledge_article_trash_notification', {
                    'articles': main_articles,
                    'recipient': partner,
                    'child_articles': children,
                })

            # If multiple "main articles", to keep sending only one mail,
            # don't link the notification to any document.
            document_to_notify = main_articles if len(main_articles) == 1 else self.env['mail.thread']
            sent_messages += document_to_notify.with_context(lang=partner_lang).message_notify(
                body=body,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=partner.ids,
                subject=subject,
            )

        return sent_messages

    # ------------------------------------------------------------
    # BUSINESS METHODS
    # ------------------------------------------------------------

    def create_article_from_template(self):
        self.ensure_one()
        article = self.env["knowledge.article"].article_create(is_private=True)
        article.apply_template(self.id, skip_body_update=False)
        return article.id

    def apply_template(self, template_id, skip_body_update=False):
        """Applies the given template on the current article
        :param int template_id: Template id
        :param boolean skip_body_update: Whether the method should skip writing
          the body and return it for further management by the caller. Note that
          this does to apply to child articles as they are not managed the same
          way and are side records. Typically
          - False: when creating a template based article from scratch;
          - True: in other cases to avoid collaborative issues (write on
            body should be done at client side);
        :return str: body of the article, used notably client side for
          collaborative mode
        """
        self.ensure_one()
        template = self.env['knowledge.article'].browse(template_id)
        template.ensure_one()

        # The following algorithm will proceed in 3 steps:
        # 1. In the first step, we will recursively create the articles and the
        #    stages following the same structure as the templates. This will
        #    ensure that the records exist in the database for the following steps.
        # 2. In the second step, we will build a dict mapping the template
        #    xml ids with the article ids created from it. The dict will be
        #    used to convert the template xml ids mentionned in the templates
        #    with the ids of the articles generated from them.
        # 3. In the third step, we will populate the articles using the values
        #    set on the associated templates.

        # Step 1: Create the articles and the stages

        template_to_article_pairs = []
        stack = [(template, self)]

        while stack:
            (parent_template, parent_article) = stack.pop()
            template_to_article_pairs.append((parent_template, parent_article))

            # Create the stages:
            parent_template_stages = self.env['knowledge.article.stage'].search([
                ('parent_id', '=', parent_template.id)
            ])
            parent_article_stages = self.env['knowledge.article.stage'].create([{
                'name': stage.name,
                'sequence': stage.sequence,
                'fold': stage.fold,
                'parent_id': parent_article.id
            } for stage in parent_template_stages])

            # Create the child articles:
            child_templates = parent_template.child_ids.sorted(
                lambda template: (template.write_date, template.id))
            if not child_templates:
                continue

            child_articles_values = []
            for template in child_templates:
                article_values = {
                    'is_article_item': template.is_article_item,
                    'parent_id': parent_article.id,
                }
                article_stage = next((article_stage for (article_stage, template_stage) in \
                    zip(parent_article_stages, parent_template_stages) \
                        if template_stage == template.stage_id), False)
                if article_stage:
                    article_values['stage_id'] = article_stage.id
                child_articles_values.append(article_values)

            child_articles = self.env['knowledge.article'].create(child_articles_values)
            stack.extend(zip(child_templates, child_articles))

        # Step 2: Build the dict mapping the template xml ids with the article ids

        template_xml_id_to_article_id_mapping = {}
        all_ir_model_data = self.env['ir.model.data'].sudo().search([
            ('model', '=', 'knowledge.article'),
            ('res_id', 'in', [template.id for (template, _) in template_to_article_pairs])
        ])

        for (template, article) in template_to_article_pairs:
            ir_model_data = all_ir_model_data.filtered(
                lambda ir_model_data: ir_model_data.res_id == template.id)

            if ir_model_data:
                template_xml_id = 'knowledge.' + ir_model_data.name
                template_xml_id_to_article_id_mapping[template_xml_id] = article.id

        # When rendering the template, the `ref` function should return the id
        # of the article created from the template having the given xml id.
        # This will ensure that the ids stored in the body of the newly created
        # article will refer to the right article and not to the original template.

        def ref(xml_id):
            return template_xml_id_to_article_id_mapping[xml_id] \
                if xml_id in template_xml_id_to_article_id_mapping \
                    else self.env.ref(xml_id).id

        # Step 3: Copy the template values to the new articles

        (root_template, root_article) = template_to_article_pairs.pop(0)
        for (template, article) in reversed(template_to_article_pairs):
            article.write({
                'article_properties': template.article_properties or {},
                'article_properties_definition': template.article_properties_definition,
                'body': template._render_template(ref),
                'cover_image_id': template.cover_image_id.id,
                'full_width': template.full_width,
                'icon': template.icon,
                'name': template.template_name,
            })

        values = {
            'article_properties': root_template.article_properties or {},
            'article_properties_definition': root_template.article_properties_definition,
            'cover_image_id': root_template.cover_image_id.id,
            'full_width': root_template.full_width,
            'icon': root_template.icon,
            'name': root_article.name or root_template.template_name,
        }
        body = root_template._render_template(ref)
        if not skip_body_update:
            values['body'] = body
        root_article.write(values)

        return body

    def _render_template(self, ref=False):
        """
        Generates the HTML body based on the template content.
        :param callable ref: The `ref` function will be used to refer to an
          external record and integrate advanced elements such as embedded views
          of article items and article links.
        """
        self.ensure_one()
        if not self.is_template or not self.template_body:
            return False

        if not ref:
            def ref(xml_id):
                return self.env.ref(xml_id).id

        def transform_xmlid_to_res_id(match):
            return str(ref(match.group('xml_id')))

        fragment = html.fragment_fromstring(self.template_body, create_parent='div')
        for element in fragment.xpath('//*[@data-behavior-props]'):
            # When encoding the "behavior props", we find and replace the function
            # calls of `ref` with the ids returned by the given `ref` function for
            # the given xml ids. The generated HTML will then only contain ids.
            # Example:
            # When the "behavior props" contains `ref('knowledge.article_template_1')`,
            # we replace that string occurence with the id returned by the given
            # `ref` function evaluated with the xml_id 'knowledge.article_template_1'.
            behavior_props = ast.literal_eval(re.sub(
                r'(?<![\w])ref\(\'(?P<xml_id>\w+\.\w+)\'\)',
                transform_xmlid_to_res_id,
                element.get('data-behavior-props')))
            element.set('data-behavior-props',
                parse.quote(json.dumps(behavior_props), safe="()*!'"))
            if 'o_knowledge_behavior_type_article' in element.get('class'):
                element.set('href', '/knowledge/article/%s' % (behavior_props.get('article_id')))

        return ''.join(html.tostring(child, encoding='unicode', method='html') \
            for child in fragment.getchildren()) # unwrap the elements from the parent node

    def create_default_item_stages(self):
        """ Need to create stages if this article has no stage yet. """
        stage_count = self.env['knowledge.article.stage'].search_count(
            [('parent_id', '=', self.id)])
        if not stage_count:
            self.env['knowledge.article.stage'].create([{
                "name": stage_name,
                "sequence": sequence,
                "parent_id": self.id,
                "fold": fold
            } for stage_name, sequence, fold in [
                (_("New"), 0, False), (_("Ongoing"), 1, False), (_("Done"), 2, True)]
            ])

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    @api.model
    def _extract_icon_from_name(self, name):
        """ See name_create / _name_search overrides for details. """
        if not isinstance(name, str) or len(name) < 3:
            return name, None

        # we consider that a non-alphabetical and non-special character is an emoji
        emoji_match = re.match(r'([^\w.,;:_%+!\\/@$€#&()*=~-]) (.*)', name)
        if not emoji_match or len(emoji_match.groups()) != 2:
            return name, None

        emoji = emoji_match.groups(1)[0]
        article_name = emoji_match.groups(1)[1]
        return article_name, emoji

    def _get_ancestor_ids(self):
        """ Return the union of sets including the ids for the ancestors of
        records in recordset. E.g.,
         * if self = Article `8` which has for parent `4` that has itself
           parent `2`, return `{2, 4}`;
         * if article `11` is a child of `6` and is also in `self`, return
           `{2, 4, 6}`;

        :rtype: set
        """
        ancestor_ids = set()
        for article in self:
            if article.id in ancestor_ids:
                continue
            for ancestor_id in map(int, article.parent_path.split('/')[-3::-1]):
                if ancestor_id in ancestor_ids:
                    break
                ancestor_ids.add(ancestor_id)
        return ancestor_ids

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
                ('user_id', '=', self.env.uid), ('is_article_active', '=', True)
            ], limit=1).article_id
        if not article:
            # retrieve workspace articles first, then private/shared ones.
            article = self.search(
                expression.AND([
                    [('parent_id', '=', False), ('is_template', '=', False)],
                    self._get_read_domain(),
                ]),
                limit=1,
                order='sequence, internal_permission desc'
            )
        return article

    def get_valid_parent_options(self, search_term=""):
        """ Returns the list of articles that can be set as parent for the
        current article (to avoid recursions) """
        return self.search_read(
            domain=[
                '&', '&', '&', '&', '&',
                    ('is_template', '=', False),
                    ('name', 'ilike', search_term),
                    ('id', 'not in', self.ids),
                    '!', ('parent_id', 'child_of', self.ids),
                    ('user_has_access', '=', True),
                    ('is_article_item', '=', False),
            ],
            fields=['id', 'display_name', 'root_article_id'],
            limit=15,
        )

    def _get_descendants(self):
        """ Returns the descendants recordset of the current article. """
        return self.env['knowledge.article'].search([('id', 'not in', self.ids), ('parent_id', 'child_of', self.ids)])

    @api.model
    def get_empty_list_help(self, help_message):
        # Meant to target knowledge_article_action_trashed action only.
        # -> Use the specific context key of that action to target it.
        if not "search_default_filter_trashed" in self.env.context:
            return super().get_empty_list_help(help_message)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        limit_days = get_param('knowledge.knowledge_article_trash_limit_days')
        try:
            limit_days = int(limit_days)
        except ValueError:
            limit_days = self.DEFAULT_ARTICLE_TRASH_LIMIT_DAYS
        title = _("No Article in Trash")
        description = Markup(
            _("""Deleted articles are stored in Trash an extra <b>%(threshold)s</b> days
                 before being permanently removed for your database""")) % {"threshold": limit_days}

        return super().get_empty_list_help(
            f'<p class="o_view_nocontent_smiling_face">{title}</p><p>{description}</p>'
        )

    def get_visible_articles(self, root_articles_ids, unfolded_ids):
        """ Get the articles that are visible in the sidebar with the given
        root articles and unfolded ids.

        An article is visible if it is a root article, or if it is a child
        article (not item) of an unfolded visible article.
        """
        if root_articles_ids:
            visible_articles_domain = [
            '|',
                ('id', 'in', root_articles_ids),
                '&',
                    '&',
                        ('parent_id', 'in', unfolded_ids),
                        ('id', 'child_of', root_articles_ids),  # Don't fetch hidden unfolded
                    ('is_article_item', '=', False)
            ]

            return self.env['knowledge.article'].search(
                visible_articles_domain,
                order='sequence, id',
            )
        return self.env['knowledge.article']

    def get_sidebar_articles(self, unfolded_ids=False):
        """ Get the data used by the sidebar on load in the form view.
        It returns some information from every article that is accessible by
        the user and that is either:
            - a visible root article
            - a favorite article or a favorite item (for the current user)
            - the current article (except if it is a descendant of a hidden
              root article or of an non accessible article - but even if it is
              a hidden root article)
            - an ancestor of the current article, if the current article is
              shown
            - a child article of any unfolded article that is shown
        """

        root_articles_domain = [
            ("parent_id", "=", False),
            ("is_template", "=", False)
        ]
        if self.env.user._is_internal():
            # Do not fetch articles that the user did not join (articles with
            # internal permissions may be set as visible to members only)
            root_articles_domain.append(("is_article_visible", "=", True))
        else:
            # Do not fetch private articles of other users for portal user
            expression.AND([root_articles_domain, ['|', ('user_has_access', '=', True), ('category', '!=', 'private')]])

        # Fetch root article_ids as sudo, ACLs will be checked on next global call fetching 'all_visible_articles'
        # this helps avoiding 2 queries done for ACLs (and redundant with the global fetch)
        root_articles_ids = self.env['knowledge.article'].sudo().search(root_articles_domain).ids

        favorite_articles_ids = self.env['knowledge.article.favorite'].sudo().search(
            [("user_id", "=", self.env.user.id), ('is_article_active', '=', True)]
        ).article_id.filtered(lambda article: article.user_has_access).ids

        # Add favorite articles and items (they are root articles in the
        # favorite tree)
        root_articles_ids += favorite_articles_ids

        if unfolded_ids is False:
            unfolded_ids = []

        # Add active article and its parents in list of unfolded articles
        if self.is_article_visible:
            if self.parent_id:
                unfolded_ids += self._get_ancestor_ids()
        # If the current article is a hidden root article, show the article
        elif not self.parent_id and self.id:
            root_articles_ids += [self.id]

        all_visible_articles = self.get_visible_articles(root_articles_ids, unfolded_ids)

        return {
            "articles": all_visible_articles.read(
                ['name', 'icon', 'parent_id', 'category', 'is_locked', 'user_can_write', 'is_user_favorite', 'is_article_item', 'has_article_children'],
                None,  # To not fetch the name of parent_id
            ),
            "favorite_ids": favorite_articles_ids,
        }
