# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tests.test_performance import UtilPerf
import random


class TestBlogPerformance(UtilPerf):
    def setUp(self):
        super().setUp()
        # if website_livechat is installed, disable it
        if 'channel_id' in self.env['website']:
            self.env['website'].search([]).channel_id = False

    def test_10_perf_sql_blog_standard_data(self):
        self.assertEqual(self._get_url_hot_query('/blog'), 11)
        self.assertLessEqual(self._get_url_hot_query('/blog', cache=False), 26)

    def test_20_perf_sql_blog_bigger_data_scaling(self):
        BlogPost = self.env['blog.post']
        BlogTag = self.env['blog.tag']
        blogs = self.env['blog.blog'].search([])
        blog_tags = BlogTag.create([{'name': 'Blog Tag Test %s' % i} for i in range(1, 20)])
        BlogPost.create([{'name': 'Blog Post Test %s' % i, 'is_published': True, 'blog_id': blogs[i % 2].id} for i in range(1, 20)])
        blog_posts = BlogPost.search([])
        for blog_post in blog_posts:
            blog_post.tag_ids += blog_tags
            blog_tags = blog_tags[:-1]
        self.assertEqual(self._get_url_hot_query('/blog'), 11)
        self.assertLessEqual(self._get_url_hot_query('/blog', cache=False), 33)
        self.assertLessEqual(self._get_url_hot_query(blog_post[0].website_url), 16)
        self.assertLessEqual(self._get_url_hot_query(blog_post[0].website_url, cache=False), 20)

    def test_30_perf_sql_blog_bigger_data_scaling(self):
        BlogPost = self.env['blog.post']
        BlogTag = self.env['blog.tag']
        blogs = self.env['blog.blog'].search([])
        blog_tags = BlogTag.create([{'name': 'New Blog Tag Test %s' % i} for i in range(1, 50)])
        BlogPost.create([{'name': 'New Blog Post Test %s' % i, 'is_published': True, 'blog_id': blogs[random.randint(0, 1)].id} for i in range(1, 100)])
        blog_posts = BlogPost.search([])
        for blog_post in blog_posts:
            blog_post.write({'tag_ids': [[6, 0, random.choices(blog_tags.ids, k=random.randint(0, len(blog_tags)))]]})

        self.assertLessEqual(self._get_url_hot_query('/blog'), 29)
        self.assertLessEqual(self._get_url_hot_query('/blog', cache=False), 71)
        self.assertLessEqual(self._get_url_hot_query(blog_post[0].website_url), 34)
        self.assertLessEqual(self._get_url_hot_query(blog_post[0].website_url, cache=False), 33)
