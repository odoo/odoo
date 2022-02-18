# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug.urls import url_join

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
    article_permission = fields.Selection(related='article_id.internal_permission', readonly=True, store=True)
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

    def _compute_is_current_user(self):
        for member in self:
            member.is_current_user = member.partner_id.user_id == self.env.user


class Article(models.Model):
    _name = "knowledge.article"
    _description = "Knowledge Articles"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "favourite_count, create_date desc"

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

    # Access rules and members + implied category
    internal_permission = fields.Selection([
        ('none', 'None'),
        ('read', 'Read'),
        ('write', 'Write'),
    ], required=True, default='write', help="Basic permission for all internal users. External users can still have permissions if they are added to the members.")
    partner_ids = fields.Many2many("res.partner", "knowledge_article_member_rel", 'article_id', 'partner_id', string="Article Members", copy=False, depends=['article_member_ids'],
        help="Article members are the partners that have specific access rules on the related article.")
    article_member_ids = fields.One2many('knowledge.article.member', 'article_id', string='Members Information', depends=['partner_ids'])  # groups ?
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

    @api.constrains('internal_permission', 'partner_ids')
    def _check_members(self):
        """ If article has no member, the internal_permission must be write. as article must have at least one writer.
        If article has member, the validation is done in article.member model has we cannot trigger constraint depending
        on fields from related model. see _check_members from 'knowledge.article.member' model for more details. """
        for article in self:
            if article.internal_permission != 'write' and not article.partner_ids:
                raise ValidationError(_("You must have at least one writer."))

    ##############################
    # Computes, Searches, Inverses
    ##############################

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_user_has_access(self):
        if self.env.user.has_group('base.group_system'):
            self.user_has_access = True
            return
        partner_id = self.env.user.partner_id
        if not partner_id:
            self.user_has_access = False
            return
        # TODO DBE: check why it doesn't work with self.env['knowledge.article.member'].sudo()
        result = self.article_member_ids.sudo().search_read([('partner_id', '=', partner_id.id)], ['article_id', 'permission'])
        member_permissions = {r["article_id"][0]: r["permission"] for r in result}
        for article in self:
            if self.env.user.share:
                article.user_has_access = member_permissions.get(article.id, "none") != "none"
            else:
                article.user_has_access = member_permissions[article.id] != "none" if article.id in member_permissions \
                    else article.internal_permission != 'none'

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
        # TODO DBE: check why it doesn't work with self.env['knowledge.article.member'].sudo()
        result = self.article_member_ids.sudo().search_read([('partner_id', '=', partner_id.id)], ['article_id', 'permission'])
        member_permissions = {r["article_id"][0]: r["permission"] for r in result}
        for article in self:
            if self.env.user.share:
                article.user_can_write = member_permissions.get(article.id, "none") == "write"
            else:
                # You cannot have only one member per article.
                article.user_can_write = member_permissions[article.id] == "write" if article.id in member_permissions \
                    else article.internal_permission == 'write'

    @api.depends('internal_permission', 'article_member_ids.permission', 'article_member_ids.partner_id')
    def _compute_category(self):
        for article in self:
            if article.internal_permission != 'none':
                article.category = 'workspace'
            elif len(article.partner_ids) > 1:
                article.category = 'shared'
            elif len(article.partner_ids) == 1 and article.article_member_ids.permission == 'write':
                article.category = 'private'
            else:  # should never happen. If an article has no category, there is an error in it's access rules.
                article.category = False

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_owner_id(self):
        for article in self:
            members = article.article_member_ids
            if article.internal_permission != 'none':
                article.owner_id = False
            elif len(members) == 1 and members.permission == 'write' and not members.partner_id.partner_share and members.partner_id.user_ids:
                article.owner_id = next(user for user in members.partner_id.user_ids if not user.share)
            else:
                article.owner_id = False

    def _search_user_has_access(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError("unsupported search operator")
        user_members = self.env['knowledge.article.member'].search(
            [('partner_id', '=', self.env.user.partner_id.id)])
        articles_with_no_access = user_members.filtered(
            lambda member: member.permission == 'none').mapped('article_id').ids
        articles_with_access = user_members.filtered(
            lambda member: member.permission != 'none').mapped('article_id').ids

        # If searching articles for which user has access.
        if (value and operator == '=') or (not value and operator == '!='):
            if self.env.user.has_group('base.group_system'):
                return expression.TRUE_DOMAIN
            elif self.env.user.share:
                return [('id', 'in', articles_with_access)]
            return ['|', '&', ('internal_permission', '!=', 'none'), ('id', 'not in', articles_with_no_access),
                         ('id', 'in', articles_with_access)]
        # If searching articles for which user has NO access.
        if self.env.user.has_group('base.group_system'):
            return expression.FALSE_DOMAIN
        elif self.env.user.share:
            return [('id', 'not in', articles_with_access)]
        return ['|', '&', ('internal_permission', '=', 'none'), ('id', 'not in', articles_with_access),
                     ('id', 'in', articles_with_no_access)]

    def _search_user_can_write(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError("unsupported search operator")
        user_members = self.env['knowledge.article.member'].search(
            [('partner_id', '=', self.env.user.partner_id.id)])
        articles_with_no_access = user_members.filtered(
            lambda member: member.permission != 'write').mapped('article_id').ids
        articles_with_access = user_members.filtered(
            lambda member: member.permission == 'write').mapped('article_id').ids

        # If searching articles for which user has write access.
        if self.env.user.has_group('base.group_system'):
            return expression.TRUE_DOMAIN
        elif self.env.user.share:
            return [('id', 'in', articles_with_access)]
        if (value and operator == '=') or (not value and operator == '!='):
            return ['|', '&', ('internal_permission', '=', 'write'), ('id', 'not in', articles_with_no_access),
                         ('id', 'in', articles_with_access)]
        # If searching articles for which user has NO write access.
        if self.env.user.has_group('base.group_system'):
            return expression.FALSE_DOMAIN
        elif self.env.user.share:
            return [('id', 'not in', articles_with_access)]
        return ['|', '&', ('internal_permission', '!=', 'write'), ('id', 'not in', articles_with_access),
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
            domain = expression.AND([domain, [('partner_ids.user_ids', 'in' if operator == '=' else 'not in', value)]])
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

    #####################
    #  Business methods
    #####################

    def move_to(self, parent_id=False, before_article_id=False, private=False):
        self.ensure_one()
        parent = self.browse(parent_id) if parent_id else False
        if parent_id and not parent:
            raise UserError(_("The parent in which you want to move your article does not exist"))
        before_article = self.browse(before_article_id) if before_article_id else False
        if before_article_id and not before_article:
            raise UserError(_("The article before which you want to move your article does not exist"))

        if before_article:
            sequence = before_article.sequence
        else:
            # get max sequence among articles with the same parent
            sequence = self._get_max_sequence_inside_parent(parent_id)

        values = {
            'parent_id': parent_id,
            'sequence': sequence
        }
        if not parent_id:
            # If parent_id, the write method will set the internal_permission based on the parent.
            # If moved from workspace to private -> set none. If moved from private to workspace -> set write
            values['internal_permission'] = 'none' if private else 'write'

        if not parent and private:  # If set private without parent, remove all members except current user.
            self.article_member_ids.unlink()
            values.update({
                'article_member_ids': [(0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                })]
            })
        elif parent:
            values.update(self._get_access_values_from_parent(parent))

        self.write(values)

        if self.child_ids:
            self._propagate_access_to_children()

        return True

    def article_create(self, title=False, parent_id=False, private=False):
        Article = self.env['knowledge.article']
        parent = Article.browse(parent_id) if parent_id else False
        if parent_id and not parent:
            raise UserError(_("The parent in which you want to move your article does not exist"))

        if parent and private:
            if not parent.owner_id == self.env.user:
                raise UserError(_("Cannot write under a non-owned private article"))
        values = {
            'internal_permission': 'none' if private else 'write',  # you cannot create an article without parent in shared directly.,
            'parent_id': parent_id,
            'sequence': self._get_max_sequence_inside_parent(parent_id)
        }
        # User cannot write on members, sudo is needed to allow to create a private article.
        if private and self.env.user.has_group('base.group_user'):
            Article = Article.sudo()
        if not parent and private:
            # To be private, the article need at least one member with write access.
            values.update({
                'article_member_ids': [(0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                })]
            })
        elif parent:
            values.update(self._get_access_values_from_parent(parent))

        if title:
            values.update({
                'name': title,
                'body': title
            })

        article = Article.create(values)

        return article.id

    def set_member_permission(self, member_id, permission):
        self.ensure_one()
        if self.user_can_write:
            member = self.sudo().article_member_ids.filtered(lambda member: member.id == member_id)
            member.write({'permission': permission})

    def remove_member(self, member_id):
        # TODO: Maybe remove member should take partner_id and simply remove it from article.partner_ids
        self.ensure_one()
        if self.user_can_write:
            member = self.sudo().article_member_ids.filtered(lambda member: member.id == member_id)
            member.unlink()

    def invite_member(self, access_rule, partner_id=False, email=False):
        self.ensure_one()
        if self.user_can_write:
            # A priori no reason to give a wrong partner_id at this stage as user must be logged in and have access.
            partner = self.env['res.partner'].browse(partner_id)
            self.sudo()._invite_member(access_rule, partner=partner, email=email)
        else:
            raise UserError(_("You cannot give access to this article as you are not editor."))

    def _invite_member(self, access_rule, partner=False, email=False):
        self.ensure_one()
        if not email and not partner:
            raise UserError(_('You need to provide an email address or a partner to invite a member.'))
        if email and not partner:
            try:
                partner = self.env["res.partner"].find_or_create(email, assert_valid_email=True)
            except ValueError:
                raise ValueError(_('The given email address is incorrect.'))

        # add member
        self.write({
            'article_member_ids': [(0, 0, {
                'partner_id': partner.id,
                'permission': access_rule
            })]
        })
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
        self.invite_member(access_rule='write', email="dbe@odoo.com") # partner=self.env.ref('base.partner_demo'),

    ###########
    #  Tools
    ###########

    def _propagate_access_to_children(self):
        """ Propagate the access rule and members of the current article to its children.
        Only the children the user can write on will be updated. """
        # Propagate access rules to children (only the ones we can write on)
        write_child_ids = self.child_ids.filtered(lambda child: child.user_can_write)
        if not write_child_ids:
            return

        for child in self.child_ids:
            write_values = child._get_access_values_from_parent(self)
            if write_values:
                child.write(write_values)
                child._propagate_access_to_children()

    def _get_access_values_from_parent(self, parent):
        """ Copy the access rule and members from the given parent to the current article.
        In case of conflict, the highest permission is kept between parent.member and article.member (write > read)
        Called by move_to and _propagate_access_to_children -> when moving an article under a parent
        Directly modifies the given write_values"""
        if not parent.user_can_write:
            # When propagating to children, this should never raise.
            raise AccessError(_("You cannot move articles under an article you can't write on"))
        values = {}
        if parent.internal_permission != self.internal_permission:
            values['internal_permission'] = parent.internal_permission
        if parent.article_member_ids:
            # add the parent's members.
            values['article_member_ids'] = [(0, 0, {
                'partner_id': member.partner_id.id,
                'permission': member.permission
            }) for member in parent.article_member_ids if member.partner_id not in self.partner_ids]

            # Modify article member in case of conflict: use highest permission
            permission_priority = {'none': 0, 'read': 1, 'write': 2}
            for member in self.article_member_ids:
                parent_member_permission = parent.article_member_ids.filtered(
                    lambda p_member: p_member.partner_id == member.partner_id).permission
                if parent_member_permission and permission_priority[parent_member_permission] > permission_priority[member.permission]:
                    values['article_member_ids'].push((1, member.id, {
                        'permission': parent_member_permission
                    }))
        return values

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
