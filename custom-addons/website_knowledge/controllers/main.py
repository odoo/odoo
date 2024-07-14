# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http, _
from odoo.http import request
from odoo.addons.knowledge.controllers.main import KnowledgeController
from odoo.exceptions import AccessError
from odoo.osv import expression


class KnowledgeWebsiteController(KnowledgeController):

    _KNOWLEDGE_TREE_ARTICLES_LIMIT = 50

    # ------------------------
    # Article Access Routes
    # ------------------------

    @http.route('/knowledge/home', type='http', auth='public', website=True, sitemap=False)
    def access_knowledge_home(self):
        if request.env.user._is_public():
            article = request.env["knowledge.article"]._get_first_accessible_article()
            if not article:
                raise werkzeug.exceptions.NotFound()
            return request.redirect("/knowledge/article/%s" % article.id)
        return super().access_knowledge_home()

    # Override routes to display articles to public users
    @http.route('/knowledge/article/<int:article_id>', type='http', auth='public', website=True, sitemap=False)
    def redirect_to_article(self, **kwargs):
        if request.env.user._is_public():
            article = request.env['knowledge.article'].sudo().browse(kwargs['article_id'])
            if not article.exists():
                raise werkzeug.exceptions.NotFound()
            if article.website_published:
                return self._redirect_to_public_view(article, kwargs.get('no_sidebar', False))
            # public users can't access articles that are not published, let them login first
            return request.redirect('/web/login?redirect=/knowledge/article/%s' % kwargs['article_id'])
        return super().redirect_to_article(**kwargs)

    def _redirect_to_public_view(self, article, no_sidebar=False):
        # The sidebar is hidden if no_sidebar is True or if there is no article
        # to show in the sidebar (i.e. no published root workspace article).
        show_sidebar = False if no_sidebar else request.env["knowledge.article"].search_count(
            self._prepare_public_root_articles_domain(), limit=1
        )
        return request.render('website_knowledge.article_view_public', {
            'article': article,
            'show_sidebar': show_sidebar
        })

    # ------------------------
    # Articles tree generation
    # ------------------------

    @http.route('/knowledge/public_sidebar', type='json', auth='public')
    def get_public_sidebar(self, active_article_id=False, unfolded_articles_ids=False, search_term=False):
        """ Public access for the sidebar.
        If a search_term is given, show the articles matching this search_term in the sidebar.
        In that case, unfolded_articles_ids is ignored (the children of the matching articles
        are not shown).
        """
        if search_term:
            public_sidebar_values = self._prepare_public_sidebar_search_values(search_term, active_article_id)
        else:
            public_sidebar_values = self._prepare_public_sidebar_values(active_article_id, unfolded_articles_ids)
        return request.env['ir.qweb']._render('website_knowledge.public_sidebar', public_sidebar_values)

    @http.route('/knowledge/public_sidebar/load_more', type='json', auth='public')
    def public_sidebar_load_more(self, limit, offset, active_article_id=False, parent_id=False):
        """" Route called when loading more articles in a particular sub-tree.

        Fetching is done based either on a parent, either on root articles when no parent is
        given.
        "limit" and "offset" allow controlling the returned result size.

        In addition, if we receive an 'active_article_id', it is forcefully displayed even if not
        in the first 50 articles of its own subtree.
        (Subsequently, all his parents are also forcefully displayed).
        That allows the end-user to always see where he is situated within the articles hierarchy.

        See 'articles_template' template docstring for details. """

        if parent_id:
            parent_id = int(parent_id)
            articles_domain = [('parent_id', '=', parent_id), ('website_published', '=', True)]
        else:
            # root articles
            articles_domain = self._prepare_public_root_articles_domain()

        offset = int(offset)
        limit = int(limit)
        articles = request.env['knowledge.article'].search(
            articles_domain,
            limit=limit + 1,
            offset=offset,
            order='sequence, id',
        )

        if len(articles) < limit:
            articles_left_count = len(articles)
        else:
            articles_left_count = request.env['knowledge.article'].search_count(articles_domain) - offset

        active_article_ancestor_ids = []
        unfolded_articles_ids = []
        force_show_active_article = False
        if articles and active_article_id and active_article_id not in articles.ids:
            active_article_with_ancestors = request.env['knowledge.article'].search(
                [('id', 'parent_of', active_article_id)]
            )
            active_article = active_article_with_ancestors.filtered(
                lambda article: article.id == active_article_id)
            active_article_ancestors = active_article_with_ancestors - active_article
            unfolded_articles_ids = active_article_ancestors.ids

            # we only care about articles our current hierarchy (base domain)
            # and that are "next" (based on sequence of last article retrieved)
            force_show_domain = expression.AND([
                articles_domain,
                [('sequence', '>', articles[-1].sequence)]
            ])
            force_show_active_article = active_article.filtered_domain(force_show_domain)
            active_article_ancestors = active_article_ancestors.filtered_domain(force_show_domain)
            active_article_ancestor_ids = active_article_ancestors.ids

            if active_article_ancestors and not any(
                    ancestor_id in articles.ids for ancestor_id in active_article_ancestors.ids):
                articles |= active_article_ancestors

        return request.env['ir.qweb']._render('website_knowledge.articles_template', {
            "active_article_id": active_article_id,
            "active_article_ancestor_ids": active_article_ancestor_ids,
            "articles": articles,
            "articles_count": articles_left_count,
            "articles_displayed_limit": self._KNOWLEDGE_TREE_ARTICLES_LIMIT,
            "articles_displayed_offset": offset,
            "has_parent": bool(parent_id),
            "force_show_active_article": force_show_active_article,
            "unfolded_articles_ids": unfolded_articles_ids,
        })

    @http.route('/knowledge/public_sidebar/children', type='json', auth='public')
    def get_public_sidebar_children(self, parent_id):
        parent = request.env['knowledge.article'].search([('id', '=', parent_id)])
        if not parent:
            raise AccessError(_("This Article cannot be unfolded. Either you lost access to it or it has been deleted."))

        articles = parent.child_ids.filtered(
            lambda a: not a.is_article_item
        ).sorted("sequence") if parent.has_article_children else request.env['knowledge.article']
        return request.env['ir.qweb']._render('website_knowledge.articles_template', {
            'articles': articles,
            "articles_displayed_limit": self._KNOWLEDGE_TREE_ARTICLES_LIMIT,
            "articles_displayed_offset": 0,
            "has_parent": True,
        })

    # --------------------
    # Articles tree utils
    # --------------------

    def _prepare_public_root_articles_domain(self):
        """ Public root articles are root articles that are published and in the workspace
        """
        return [("parent_id", "=", False), ("category", "=", "workspace"), ("website_published", "=", True)]

    def _prepare_public_sidebar_values(self, active_article_id, unfolded_articles_ids):
        """ Prepares all the info needed to render the sidebar in public

        :param int active_article_id: used to highlight the given article_id in the template;
        :param unfolded_articles_ids: List of IDs used to display the children
          of the given article ids. Unfolded articles are saved into local storage.
          When reloading/opening the article page, previously unfolded articles
          nodes must be opened;
        """
        # Sudo to speed up the search, as permissions will be computed anyways
        # when getting the visible articles
        root_articles_ids = request.env['knowledge.article'].sudo().search(
            self._prepare_public_root_articles_domain(), order="sequence, id"
        ).ids

        active_article_ancestor_ids = []
        unfolded_ids = unfolded_articles_ids or []

        # Add active article and its parents in list of unfolded articles
        active_article = request.env['knowledge.article'].sudo().browse(active_article_id)
        if active_article and active_article.parent_id:
            active_article_ancestor_ids = active_article._get_ancestor_ids()
            unfolded_ids += active_article_ancestor_ids

        all_visible_articles = request.env['knowledge.article'].get_visible_articles(root_articles_ids, unfolded_ids)

        return {
            "active_article_id": active_article_id,
            "active_article_ancestor_ids": active_article_ancestor_ids,
            "articles_displayed_limit": self._KNOWLEDGE_TREE_ARTICLES_LIMIT,
            "articles_displayed_offset": 0,
            "all_visible_articles": all_visible_articles,
            "root_articles": all_visible_articles.filtered(lambda article: not article.parent_id),
            "unfolded_articles_ids": unfolded_ids,
        }

    def _prepare_public_sidebar_search_values(self, search_term, active_article_id=False):
        """  Prepares all the info needed to render the sidebar given the search_term in public.

            The tree is completely flattened (no sections nor child articles) to avoid noise
            (unnecessary parents display when children are matching) and redondancy (duplicated articles
            because of the favorite tree).

            :param int active_article_id: used to highlight the given article_id in the template;
            :param string search_term: user search term to filter the articles on;
        """

        # Get all the visible articles based on the search term
        all_visible_articles = request.env['knowledge.article'].search(
            expression.AND([[('is_article_item', '=', False)], [('name', 'ilike', search_term)]]),
            order='name',
            limit=self._KNOWLEDGE_TREE_ARTICLES_LIMIT,
        )

        return {
            "search_tree": True,  # Display the flatenned tree instead of the basic tree with sections
            "active_article_id": active_article_id,
            "articles_displayed_limit": self._KNOWLEDGE_TREE_ARTICLES_LIMIT,
            'articles': all_visible_articles,
        }
