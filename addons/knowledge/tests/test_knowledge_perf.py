# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime
from odoo.exceptions import AccessError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

print('test')
@tagged('dbetest')
class TestKnowledgePerf(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Keep a limited setup to ensure tests are not impacted by other
        records created in CRM common. """
        super(TestKnowledgePerf, cls).setUpClass()
        Article = cls.env['knowledge.article']
        permissions = {0: "none", 1: "read", 2: "write"}

        groups = ['base.group_user', 'base.group_system', 'base.group_portal',
                  'base.group_user', 'base.group_user', 'base.group_portal']

        # users
        cls.users = cls.env['res.users']
        for i in range(0, 50):
            cls.users |= new_test_user(cls.env, login="Test_user_%s" % str(i), groups=groups[i % 6],
                                   name="Knowledge Test User #%s" % str(i), email="user_%s@knowledge.odoo.com" % str(i))

        # Root level
        _logger.warning("starting level 0")
        users = cls.users.filtered(lambda u: u.has_group('base.group_user'))
        cls.level_0_articles = Article
        cls.level_0_articles_private = Article
        for user in users[:5]:
            # create public root articles
            for i in range(0, 10):
                article = Article.browse(Article.with_user(user).article_create(title="Public Root Article #%s" % str(i)))
                cls.level_0_articles |= article
                for m in range(1, 5):
                    if m < 4 and permissions[(m+i) % 3] == 'none' and cls.users[((i+1)*m) % 50] == user:
                        print("Should lead to bug afterwards")
                    article.with_user(user).invite_member(permissions[(m+i) % 3], cls.users[((i+1)*m) % 50].partner_id.id, send_mail=False)
                # Create private root articles
                if i % 2 == 0:
                    cls.level_0_articles_private |= Article.browse(Article.with_user(user).article_create(title="Private Root Article #%s" % str(i), private=True))

        # Level 1
        cls.level_1_articles, cls.level_1_articles_private = cls.create_articles(cls,
            users[:5], cls.level_0_articles, cls.level_0_articles_private, cls.users, permissions, (2*50), 1)

        cls.level_2_articles, cls.level_2_articles_private = cls.create_articles(cls,
            users[:5], cls.level_1_articles, cls.level_1_articles_private, cls.users, permissions, (3 * 50), 2)

        cls.level_3_articles, cls.level_3_articles_private = cls.create_articles(cls,
            users[:5], cls.level_2_articles, cls.level_2_articles_private, cls.users, permissions, (4 * 50), 2)

        cls.level_4_articles, cls.level_4_articles_private = cls.create_articles(cls,
            users[:5], cls.level_3_articles, cls.level_3_articles_private, cls.users, permissions, (5 * 50), 2)

    def test_perf(self):
        # _logger.warning("starting _get_internal_permission")
        # level_4_permissions = self.level_4_articles._get_internal_permission(self.level_4_articles.ids)
        # _logger.warning("starting _get_partner_member_permissions")
        # level_4_partner_permissions = self.level_4_articles._get_partner_member_permissions(self.users[1].partner_id.id)
        # _logger.warning("starting _get_article_member_permissions")
        # level_4_member_permissions = self.level_4_articles._get_article_member_permissions()
        # _logger.warning("Finishing")

        test_user = self.users[0]
        admin_user = self.users[1]

        # Display Home View for User 1
        start = datetime.now()
        tree_value = self.get_tree_values(self.level_4_articles[0].id, test_user)
        template = self.env.ref('knowledge.knowledge_article_tree_template')._render(tree_value)
        _logger.warning("Display Home View for User 1: %s sec" % (start - datetime.now()).total_seconds())

        # Look for all the article a user has access to
        start = datetime.now()
        article_with_access = self.env["knowledge.article"].with_user(test_user).search([])
        _logger.warning("Look for all the article a user has access to: %s sec" % (start - datetime.now()).total_seconds())

        # Look for all the private article for a specified user
        start = datetime.now()
        own_private_articles = self.env["knowledge.article"].sudo().search([('owner_id', '=', admin_user.id)])
        _logger.warning("Look for all the private article for a specified user - own_private_articles: %s sec" % (start - datetime.now()).total_seconds())
        start = datetime.now()
        test_user_private_articles = self.env["knowledge.article"].sudo().search([('owner_id', '=', test_user.id)])
        _logger.warning("Look for all the private article for a specified user - test_user_private_articles: %s sec" % (start - datetime.now()).total_seconds())

        # Show all the members and permissions of a specified article
        start = datetime.now()
        # article_members = self.level_4_articles[123].sudo().with_user(admin_user)._get_article_member_permissions()
        article_members = self.level_4_articles[123].sudo().with_user(admin_user).article_member_ids
        _logger.warning("Show all the members and permissions of a specified article: %s sec" % (start - datetime.now()).total_seconds())

    def get_tree_values(self, res_id, user_id):
        # sudo article to avoid access error on member or on article for external users.
        # The article the user can see will be based on user_has_access.
        Article = self.env["knowledge.article"].sudo()
        # get favourite
        favourites = Article.search([("favourite_user_ids", "in", [user_id.id]), ('user_has_access', '=', True)])

        main_articles = Article.search([("parent_id", "=", False), ('user_has_access', '=', True)])

        public_articles = main_articles.filtered(lambda article: article.category == 'workspace')
        shared_articles = main_articles.filtered(lambda article: article.category == 'shared')

        values = {
            "active_article_id": res_id,
            "favourites": favourites,
            "public_articles": public_articles,
            "shared_articles": shared_articles
        }

        if self.env.user.has_group('base.group_user'):
            values['private_articles'] = main_articles.filtered(lambda article: article.owner_id == user_id)
        else:
            values['hide_private'] = True

        return values

    def create_articles(self, create_users, parent_ids, private_parent_ids, member_users, permissions, number_of_articles, level):
        Article = self.env['knowledge.article']
        articles = Article
        articles_private = Article
        article_range = int(number_of_articles / 5)
        for u in range(len(create_users)):
            # create public root articles
            private_user_articles = private_parent_ids.filtered(lambda a: a.owner_id == create_users[u])
            for i in range(0, article_range):
                try:
                    article = Article.browse(Article.with_user(create_users[u]).article_create(
                        title="Public Article level %s #%s" % (str(level), str(i)), parent_id=parent_ids[(i*u) % len(parent_ids)].id))
                    articles |= article
                    if i % 2 == 0: # some articles won't have specific members
                        for m in range(1, 5):
                            if m < 4 and permissions[(m + i) % 3] == 'none' and member_users[((i+1)*m) % 50] == create_users[u]:
                                print("Should lead to bug afterwards")
                            article.with_user(create_users[u]).invite_member(
                                permissions[(m+i) % 3], member_users[((i+1)*m) % 50].partner_id.id, send_mail=False)
                except AccessError:
                    pass
                # Create private root articles
                if i % 2 == 0 and private_user_articles:
                    try:
                        articles_private |= Article.browse(Article.with_user(create_users[u]).article_create(
                            title="Private Article level %s #%s" % (str(level), str(i)), private=True, parent_id=private_user_articles[(i*u) % len(private_user_articles)].id))
                    except AccessError:
                        pass

        return articles, articles_private