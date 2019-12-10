# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common as slides_common
from odoo.tests.common import users


class TestSequencing(slides_common.SlidesCase):

    @users('user_publisher')
    def test_category_update(self):
        self.assertEqual(self.channel.slide_category_ids, self.category)
        self.assertEqual(self.channel.slide_content_ids, self.slide | self.slide_2 | self.slide_3)
        self.assertEqual(self.slide.category_id, self.env['slide.slide'])
        self.assertEqual(self.slide_2.category_id, self.category)
        self.assertEqual(self.slide_3.category_id, self.category)
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.category.id, self.slide_2.id, self.slide_3.id])

        self.slide.write({'sequence': 0})
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.category.id, self.slide_2.id, self.slide_3.id])
        self.assertEqual(self.slide_2.category_id, self.category)
        self.slide_2.write({'sequence': 1})
        self.channel.invalidate_cache()
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_2.id, self.category.id, self.slide_3.id])
        self.assertEqual(self.slide_2.category_id, self.env['slide.slide'])

        channel_2 = self.env['slide.channel'].create({
            'name': 'Test2'
        })
        new_category = self.env['slide.slide'].create({
            'name': 'NewCategorySlide',
            'channel_id': channel_2.id,
            'is_category': True,
            'sequence': 1,
        })
        new_category_2 = self.env['slide.slide'].create({
            'name': 'NewCategorySlide2',
            'channel_id': channel_2.id,
            'is_category': True,
            'sequence': 2,
        })
        new_slide = self.env['slide.slide'].create({
            'name': 'NewTestSlide',
            'channel_id': channel_2.id,
            'sequence': 2,
        })
        self.assertEqual(new_slide.category_id, new_category_2)
        (new_slide | self.slide_3).write({'sequence': 1})
        self.assertEqual(new_slide.category_id, new_category)
        self.assertEqual(self.slide_3.category_id, self.env['slide.slide'])

        (new_slide | self.slide_3).write({'sequence': 0})
        self.assertEqual(new_slide.category_id, self.env['slide.slide'])
        self.assertEqual(self.slide_3.category_id, self.env['slide.slide'])

    @users('user_publisher')
    def test_resequence(self):
        self.category.write({'sequence': 4})
        self.slide_2.write({'sequence': 8})
        self.slide_3.write({'sequence': 3})

        self.channel.invalidate_cache()
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_3.id, self.category.id, self.slide_2.id])

        self.assertEqual(self.slide.sequence, 1)
        # self.channel._resequence_slides(self.slide)
        # self.channel.invalidate_cache()
        # # self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_3.id, self.category.id, self.slide_2.id])
        # self.assertEqual(self.slide_3.sequence, 2)
        # self.assertEqual(self.category.sequence, 3)
        # self.assertEqual(self.slide_2.sequence, 4)


class TestFromURL(slides_common.SlidesCase):
    def test_youtube_urls(self):
        urls = {
            'W0JQcpGLSFw': [
                'https://youtu.be/W0JQcpGLSFw',
                'https://www.youtube.com/watch?v=W0JQcpGLSFw',
                'https://www.youtube.com/watch?v=W0JQcpGLSFw&list=PL1-aSABtP6ACZuppkBqXFgzpNb2nVctZx',
            ],
            'vmhB-pt7EfA': [  # id starts with v, it is important
                'https://youtu.be/vmhB-pt7EfA',
                'https://www.youtube.com/watch?feature=youtu.be&v=vmhB-pt7EfA',
                'https://www.youtube.com/watch?v=vmhB-pt7EfA&list=PL1-aSABtP6ACZuppkBqXFgzpNb2nVctZx&index=7',
            ],
            'hlhLv0GN1hA': [
                'https://www.youtube.com/v/hlhLv0GN1hA',
                'https://www.youtube.com/embed/hlhLv0GN1hA',
                'https://m.youtube.com/watch?v=hlhLv0GN1hA'
            ],
        }

        for id, urls in urls.items():
            for url in urls:
                with self.subTest(url=url, id=id):
                    document = self.env['slide.slide']._find_document_data_from_url(url)
                    self.assertEqual(document[0], 'youtube')
                    self.assertEqual(document[1], id)
