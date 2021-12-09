# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import AccessError
from odoo.osv import expression


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
    # used to highlight the current user in the share wizard.
    is_current_user = fields.Boolean(string="Is Me ?", compute="_compute_is_current_user")

    def _compute_is_current_user(self):
        for member in self:
            member.is_current_user = member.partner_id.user_id == self.env.user


class Article(models.Model):
    _name = "knowledge.article"
    _description = "Knowledge Articles"
    _inherit = ['mail.thread']
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
    ], required=True, default='write')
    partner_ids = fields.Many2many("res.partner", "knowledge_article_member_rel", 'article_id', 'partner_id', string="Article Members", copy=False, depends=['article_member_ids'],
        help="Article members are the partners that have specific access rules on the related article.")
    article_member_ids = fields.One2many('knowledge.article.member', 'article_id', string='Members Information', depends=['partner_ids'])  # groups ?
    user_has_access = fields.Boolean(string='Has Access', compute="_compute_user_access")
    user_can_write = fields.Boolean(string='Can Write', compute="_compute_user_access")
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

    # TODO DBE: Add constraints
    # -> at least one member with write access if internal_permission != 'write'

    ##############################
    # Computes, Searches, Inverses
    ##############################

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id', 'article_member_ids.permission')
    def _compute_user_access(self):
        for article in self:
            # You cannot have only one member per article.
            user_member = article.article_member_ids.filtered(
                lambda member: self.env.user in member.partner_id.user_ids)
            article.user_has_access = user_member.permission != "none" if user_member \
                else article.internal_permission != 'none'
            article.user_can_write = user_member.permission == "write" if user_member \
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
            elif len(members) == 1 and members.permission == 'write' and not members.partner_id.partner_share:
                article.owner_id = next(user for user in members.partner_id.user_ids if not user.share)
            else:
                article.owner_id = False

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
            if vals.get('parent_id'):
                # copy members from parent
                parent = self.browse(vals['parent_id'])
                if not parent.user_can_write:
                    raise AccessError(_("You cannot create articles under an article you can't write on"))
                vals['internal_permission'] = parent.internal_permission
                if parent.article_member_ids:
                    # At creation, always take the membership of the parent
                    vals['article_member_ids'] = [(0, 0, {
                        'partner_id': member.partner_id.id,
                        'permission': member.permission
                    }) for member in parent.article_member_ids]

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

        membership_changed = False
        wrote_articles = self.env['knowledge.article']
        if vals.get('parent_id'):
            # copy members from parent
            parent = self.browse(vals['parent_id'])
            if not parent.user_can_write:
                raise AccessError(_("You cannot move articles under an article you can't write on"))
            vals['internal_permission'] = parent.internal_permission
            for article in self:  # need to do it one by one as each article has their own set of members
                if parent.article_member_ids:
                    # In case of conflict, give priority to the article's members, not parent's ones
                    article_vals = vals.copy()
                    article_vals['article_member_ids'] = [(0, 0, {
                        'partner_id': member.partner_id.id,
                        'permission': member.permission
                    }) for member in parent.article_member_ids if member.partner_id not in article.partner_ids]
                    super(Article, article).write(article_vals)
                    membership_changed = True
                    wrote_articles |= article

        result = super(Article, self - wrote_articles).write(vals)

        # Propagate access rules to children
        # TODO: /!\ What happen if you can write on parent article but not on one of the children ?
        if self.child_ids:
            children_values = {}
            if 'internal_permission' in vals:
                # Propagate permission to children
                children_values = {
                    'internal_permission': vals['internal_permission']
                }

            wrote_children = self.env['knowledge.article']
            if 'article_member_ids' in vals or membership_changed:
                # propagate members to children: need to do it one by one as each article has their own set of members
                for article in self:
                    for child in article.child_ids:
                        # In case of conflict, give priority to the article's members, not parent's ones
                        child_values = children_values.copy()
                        child_values['article_member_ids'] = [(0, 0, {
                            'partner_id': member.partner_id.id,
                            'permission': member.permission
                        }) for member in article.article_member_ids if member.partner_id not in child.partner_ids]
                        child.write(child_values)
                        wrote_children |= child

            if children_values:
                (self.child_ids - wrote_children).write(children_values)

        # use context key to stop reordering loop as "_resequence" calls write method.
        if any(field in ['parent_id', 'sequence'] for field in vals) and not self.env.context.get('resequencing_articles'):
            self.with_context(resequencing_articles=True)._resequence()

        return result

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

    ############################
    # Tools and business methods
    ############################

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

    # TODO: Check if still needed or if we will use it later.
    def _set_private(self, parent_id=False):
        self.ensure_one()
        self.internal_permission = 'none'
        self.parent_id = parent_id

        self.article_member_ids.filtered(lambda member: member.partner_id != self.env.user.partner_id).unlink()

        # update the member or add it to member with write access.
        if self.article_member_ids:
            self.article_member_ids.permission = 'write'
        else:
            self.article_member_ids = [(0, 0, {
                'article_id': self.id,
                'partner_id': self.env.user.partner_id,
                'permission': 'write'
            })]

    def _invite_partners(self, partner_ids, access_rule):
        self.ensure_one()
        # add member
        self.article_member_ids.write([(0, 0, {
            'article_id': self.id,
            'partner_id': partner.id,
            'permission': access_rule
        }) for partner in partner_ids])
        # TODO: send mail
