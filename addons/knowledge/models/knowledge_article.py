# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Article(models.Model):
    _name = "knowledge.article"
    _description = "Contains the knowledge of a specific subject."
    _order = "is_user_favourite, favourite_count, last_edition_date desc"

    name = fields.Char(string="Title")
    body = fields.Html(string="Article Body")

    parent_id = fields.Many2one("knowledge.article", string="Parent Article")
    child_ids = fields.One2many("knowledge.article", "parent_id", string="Child Articles")
    level = fields.Integer(string="Article Level", compute="_compute_level", store=True, readonly=True, recursive=True,
                           help="Level 1 are root articles that has no parent. " +
                                "Level 2 are the children of level 1, etc.")
    sequence = fields.Integer(string="Article Sequence",
                              help="The sequence is computed only among the same level under a single parent.")

    author_ids = fields.Many2many("res.users", string="Authors", default=lambda self: self.env.user)

    # TODO DBE: add authorised_user to allow users to read private article of other users. (+ access_token)
    authorised_user_ids = fields.Many2many("res.users", "knowledge_authorised_user_rel", string="Authorised Users",
                                           help="Authorised users are users that can read the article even if it's private.")

    # Same as write_uid/_date but limited to the body
    last_edition_id = fields.Many2one("res.users", string="Last Edited by")
    last_edition_date = fields.Datetime(string="Last Edited on")

    # Favourite
    is_user_favourite = fields.Boolean(string="Favourite?", compute="_compute_is_user_favourite",
                                       inverse="_inverse_is_user_favourite", search="_search_is_user_favourite")
    favourite_user_ids = fields.Many2many("res.users", "knowledge_favourite_user_rel", "article_id", "user_id",
                                          string="Favourites")
    favourite_count = fields.Integer(string="#Is Favourite")

    # Published
    website_published = fields.Boolean(string="Website Published")

    # Private ?
    owner_id = fields.Many2one("res.users", string="Current Owner",
                               help="When an article has an owner, it means this article is private for that owner.")
    is_private = fields.Boolean(string="Private", compute="_compute_is_private", inverse="_inverse_is_private")

    @api.depends("parent_id.level")
    def _compute_level(self):
        for article in self:
            if not article.parent_id:
                article.level = 1
            else:
                article.level = article.parent_id.level + 1

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

        articles = self.env['knowledge.article'].sudo().search(domain)

        return [('id', 'in', articles.ids)]

    @api.depends("owner_id")
    def _compute_is_private(self):
        for article in self:
            article.is_private = article.owner_id == self.env.user

    def _inverse_is_private(self):
        private_articles = public_articles = self.env['knowledge.article']
        # changing the privacy of a parent impact all his children.
        for article in self:
            def get_all_children(a):
                if a.child_ids:
                    return a.child_ids | get_all_children(a.child_ids)
                else:
                    return self.env['knowledge.article']
            children = get_all_children(article)

            if self.env.user == article.owner_id:
                public_articles |= article | children
            else:
                private_articles |= article | children

        private_articles.write({'owner_id': self.env.uid})
        public_articles.write({'owner_id': False})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['last_edition_id'] = self._uid
            vals['last_edition_date'] = fields.Datetime.now()
        return super(Article, self).create(vals_list)

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

    def unlink(self):
        for article in self:
            # Make all the article's children be adopted by the parent's parent.
            # Otherwise, we will have to manage an orphan house.
            parent = article.parent_id
            if parent:
                article.child_ids.write({"parent_id": parent.id})
        return super(Article, self).unlink()

    #TODO override search method (see crm/models/crm_lead.py #750) to allow order on is_user_favourite
    # <field name="my_activity_date_deadline" string="My Deadline" widget="remaining_days" options="{'allow_order': '1'}"/>

    def _get_highest_parent(self):
        self.ensure_one()
        if self.parent_id:
            return self.parent_id._get_highest_parent()
        else:
            return self

    def _get_max_sequence(self, parent_id):
        max_sequence_article = self.env["knowledge.article"].search(
            [("parent_id", "=", parent_id)], order="sequence desc", limit=1
        )
        return max_sequence_article.sequence if max_sequence_article else -1

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
        parents = self.mapped("parent_id")
        for parent in parents:
            children = self.search([("parent_id", '=', parent.id)], order="sequence,write_date desc")
            children_sequences = children.mapped('sequence')
            # no need to resequence if no duplicates.
            if len(children_sequences) == len(set(children_sequences)):
                continue

            # find index of duplicates
            duplicate_index = [idx for idx, item in enumerate(children_sequences) if item in children_sequences[:idx]][0]
            start_sequence = children_sequences[duplicate_index] + 1
            # only need to resequence after the duplicate
            children = children[duplicate_index:]
            for i in range(len(children)):
                if i+start_sequence not in write_vals_by_sequence:
                    write_vals_by_sequence[i+start_sequence] = children[i]
                else:
                    write_vals_by_sequence[i+start_sequence] |= children[i]

        for sequence in write_vals_by_sequence:
            write_vals_by_sequence[sequence].write({'sequence': sequence})

