# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tests.test_performance import UtilPerf
import random
import datetime
from freezegun import freeze_time


class TestBlogPerformance(UtilPerf):
    def setUp(self):
        super().setUp()
        self.env['blog.blog'].search([]).active = False
        blogs = self.env['blog.blog'].create([{
            "name": 'aaa Blog Test',
            "subtitle": 'Blog Test Subtitle',
            "cover_properties": """{"background-image": "url('/website_blog/static/src/img/blog_1.jpeg')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0.4"}""",
        }, {
            "name": 'bbb Blog Test',
            "subtitle": 'Blog Test Subtitle',
            "cover_properties": """{"background-image": "url('/website_blog/static/src/img/blog_1.jpeg')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0.4"}""",
        }])

        blog_tags = self.env['blog.tag'].create([{
            'name': 'Tag 1',
        }, {
            'name': 'Tag 2',
        }])
        self.env['blog.post'].create([{
            "name": "Post Test",
            "subtitle": "Subtitle Test",
            "blog_id": blog.id,
            "author_id": self.env.user.id,
            "tag_ids": [(4, tag.id) for tag in blog_tags],
            "is_published": True,
            "cover_properties": """{"background-image": "url('/website_blog/static/src/img/cover_1.jpg')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}""",
        } for blog in blogs])

    def test_10_perf_sql_blog_standard_data(self):
        # some blog post are published at the same time the test is run meaning that they are not published.
        # We ave multiple possibilities when _get_url_hot_query is called:
        # - all call to /blog are executed before the publication date: 9 total queries (8)
        # - some call to /blog are executed after the publication date: 11 total queries (10)
        # - only the last call (considered hot) is executed after the publication date: ~40-50 queries
        # using freezetime after the publication date ensures a consistent result
        with freeze_time(datetime.datetime.now() + datetime.timedelta(seconds=2)):
            self.assertLessEqual(self._get_url_hot_query('/blog'), 10)

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
        self.assertEqual(self._get_url_hot_query('/blog'), 10)
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
