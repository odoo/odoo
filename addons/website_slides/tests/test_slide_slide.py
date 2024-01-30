# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo.addons.website_slides.tests import common as slides_common
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestSlideInternals(slides_common.SlidesCase):

    @mute_logger('odoo.sql_db')
    @users('user_manager')
    def test_slide_create_vote_constraint(self):
        # test vote value must be 1, 0 and -1.
        with self.assertRaises(psycopg2.errors.CheckViolation), self.cr.savepoint():
            self.env['slide.slide.partner'].create({
                'slide_id': self.slide.id,
                'channel_id': self.channel.id,
                'partner_id': self.user_manager.partner_id.id,
                'vote': 2,
            })

    def test_change_content_type(self):
        """ To prevent constraint violation when changing type from video to article and vice-versa """
        slide = self.env['slide.slide'].create({
            'name': 'dummy',
            'channel_id': self.channel.id,
            'slide_category': 'video',
            'is_published': True,
            'url': 'https://youtu.be/W0JQcpGLSFw',
        })

        slide.write({'slide_category': 'article', 'html_content': '<p>Hello</p>'})
        self.assertTrue(slide.html_content)
        self.assertFalse(slide.url)

        slide.slide_category = 'document'
        self.assertFalse(slide.html_content)

class TestVideoFromURL(slides_common.SlidesCase):
    def test_video_youtube(self):
        youtube_urls = {
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
                'https://www.youtube-nocookie.com/embed/hlhLv0GN1hA',
                'https://m.youtube.com/watch?v=hlhLv0GN1hA',
            ],
        }

        Slide = self.env['slide.slide'].with_context(website_slides_skip_fetch_metadata=True)

        # test various YouTube URL formats
        for youtube_id, urls in youtube_urls.items():
            for url in urls:
                with self.subTest(url=url, id=youtube_id):
                    slide = Slide.create({
                        'name': 'dummy',
                        'channel_id': self.channel.id,
                        'url': url,
                        'slide_category': 'video'
                    })
                    self.assertEqual('youtube', slide.video_source_type)
                    self.assertEqual(youtube_id, slide.youtube_id)

    def test_video_google_drive(self):
        google_drive_urls = {
            '1qU5nHVNbz_r84P_IS5kDzoCuC1h5ZAZR': [
                'https://drive.google.com/file/d/1qU5nHVNbz_r84P_IS5kDzoCuC1h5ZAZR/view?usp=sharing',
                'https://drive.google.com/file/d/1qU5nHVNbz_r84P_IS5kDzoCuC1h5ZAZR',
            ],
        }

        Slide = self.env['slide.slide'].with_context(website_slides_skip_fetch_metadata=True)

        # test various Google Drive URL formats
        for google_drive_id, urls in google_drive_urls.items():
            for url in urls:
                with self.subTest(url=url, id=google_drive_id):
                    slide = Slide.create({
                        'name': 'dummy',
                        'channel_id': self.channel.id,
                        'url': url,
                        'slide_category': 'video'
                    })
                    self.assertEqual('google_drive', slide.video_source_type)
                    self.assertEqual(google_drive_id, slide.google_drive_id)

    def test_video_vimeo(self):
        vimeo_urls = {
            # regular URL from Vimeo
            '545859999': [
                'https://vimeo.com/545859999',
                'https://vimeo.com/545859999?autoplay=1',
            ],
            # test channel URL from Vimeo
            '551979139': [
                'https://vimeo.com/channels/staffpicks/551979139',
                'https://vimeo.com/channels/staffpicks/551979139?autoplay=1',
            ],
            # test URL from Vimeo with setting 'with URL only'
            # we need to store both the ID and the token, see '_compute_embed_code' method for details
            '545859999/94dd03ddb0': [
                'https://vimeo.com/545859999/94dd03ddb0',
                'https://vimeo.com/545859999/94dd03ddb0?autoplay=1',
            ],
        }

        Slide = self.env['slide.slide'].with_context(website_slides_skip_fetch_metadata=True)

        # test various Vimeo URL formats
        for vimeo_id, urls in vimeo_urls.items():
            for url in urls:
                with self.subTest(url=url, id=vimeo_id):
                    slide = Slide.create({
                        'name': 'dummy',
                        'channel_id': self.channel.id,
                        'url': url,
                        'slide_category': 'video'
                    })
                    self.assertEqual('vimeo', slide.video_source_type)
                    self.assertEqual(vimeo_id, slide.vimeo_id)
