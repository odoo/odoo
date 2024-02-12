# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tests import common, tagged
from odoo.addons.web_editor import tools


@tagged('post_install', '-at_install')
class TestVideoUtils(common.BaseCase):
    urls = {
        'youtube': 'https://www.youtube.com/watch?v=xCvFZrrQq7k',
        'vimeo': 'https://vimeo.com/395399735',
        'vimeo_unlisted_video': 'https://vimeo.com/795669787/0763fdb816',
        'vimeo_player': 'https://player.vimeo.com/video/395399735',
        'vimeo_player_unlisted_video': 'https://player.vimeo.com/video/795669787?h=0763fdb816',
        'dailymotion': 'https://www.dailymotion.com/video/x7svr6t',
        'youku': 'https://v.youku.com/v_show/id_XMzY1MjY4.html?spm=a2hzp.8244740.0.0',
        'instagram': 'https://www.instagram.com/p/B6dXGTxggTG/'
    }

    def test_player_regexes(self):
        #youtube
        self.assertIsNotNone(re.search(tools.player_regexes['youtube'], TestVideoUtils.urls['youtube']))
        #vimeo
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo'], TestVideoUtils.urls['vimeo']))
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo'], TestVideoUtils.urls['vimeo_unlisted_video']))
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo_player'], TestVideoUtils.urls['vimeo_player']))
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo_player'], TestVideoUtils.urls['vimeo_player_unlisted_video']))
        #dailymotion
        self.assertIsNotNone(re.search(tools.player_regexes['dailymotion'], TestVideoUtils.urls['dailymotion']))
        #youku
        self.assertIsNotNone(re.search(tools.player_regexes['youku'], TestVideoUtils.urls['youku']))
        #instagram
        self.assertIsNotNone(re.search(tools.player_regexes['instagram'], TestVideoUtils.urls['instagram']))

    def test_get_video_source_data(self):
        self.assertEqual(3, len(tools.get_video_source_data(TestVideoUtils.urls['youtube'])))
        #youtube
        self.assertEqual('youtube', tools.get_video_source_data(TestVideoUtils.urls['youtube'])[0])
        self.assertEqual('xCvFZrrQq7k', tools.get_video_source_data(TestVideoUtils.urls['youtube'])[1])
        #vimeo
        self.assertEqual('vimeo', tools.get_video_source_data(TestVideoUtils.urls['vimeo'])[0])
        self.assertEqual('395399735', tools.get_video_source_data(TestVideoUtils.urls['vimeo'])[1])
        self.assertEqual('vimeo', tools.get_video_source_data(TestVideoUtils.urls['vimeo_unlisted_video'])[0])
        self.assertEqual('795669787', tools.get_video_source_data(TestVideoUtils.urls['vimeo_unlisted_video'])[1])
        self.assertEqual('vimeo', tools.get_video_source_data(TestVideoUtils.urls['vimeo_player'])[0])
        self.assertEqual('395399735', tools.get_video_source_data(TestVideoUtils.urls['vimeo_player'])[1])
        self.assertEqual('vimeo', tools.get_video_source_data(TestVideoUtils.urls['vimeo_player_unlisted_video'])[0])
        self.assertEqual('795669787', tools.get_video_source_data(TestVideoUtils.urls['vimeo_player_unlisted_video'])[1])
        #dailymotion
        self.assertEqual('dailymotion', tools.get_video_source_data(TestVideoUtils.urls['dailymotion'])[0])
        self.assertEqual('x7svr6t', tools.get_video_source_data(TestVideoUtils.urls['dailymotion'])[1])
        #youku
        self.assertEqual('youku', tools.get_video_source_data(TestVideoUtils.urls['youku'])[0])
        self.assertEqual('XMzY1MjY4', tools.get_video_source_data(TestVideoUtils.urls['youku'])[1])
        #instagram
        self.assertEqual('instagram', tools.get_video_source_data(TestVideoUtils.urls['instagram'])[0])
        self.assertEqual('B6dXGTxggTG', tools.get_video_source_data(TestVideoUtils.urls['instagram'])[1])

    def test_get_video_url_data(self):
        self.assertEqual(2, len(tools.get_video_url_data(TestVideoUtils.urls['youtube'])))
        #youtube
        self.assertEqual('youtube', tools.get_video_url_data(TestVideoUtils.urls['youtube'])['platform'])
        #vimeo
        for key in ['vimeo', 'vimeo_player']:
            self.assertEqual(tools.get_video_url_data(TestVideoUtils.urls[key]), {
                'platform': 'vimeo',
                'embed_url': '//player.vimeo.com/video/395399735?autoplay=0'
            })
        for key in ['vimeo_unlisted_video', 'vimeo_player_unlisted_video']:
            self.assertEqual(tools.get_video_url_data(TestVideoUtils.urls[key]), {
                'platform': 'vimeo',
                'embed_url': '//player.vimeo.com/video/795669787?autoplay=0&h=0763fdb816'
            })
        #dailymotion
        self.assertEqual('dailymotion', tools.get_video_url_data(TestVideoUtils.urls['dailymotion'])['platform'])
        #youku
        self.assertEqual('youku', tools.get_video_url_data(TestVideoUtils.urls['youku'])['platform'])
        #instagram
        self.assertEqual('instagram', tools.get_video_url_data(TestVideoUtils.urls['instagram'])['platform'])

    def test_valid_video_url(self):
        self.assertIsNotNone(re.search(tools.valid_url_regex, TestVideoUtils.urls['youtube']))


@tagged('-standard', 'external')
class TestVideoUtilsExternal(common.BaseCase):
    def test_get_video_thumbnail(self):
        #youtube
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['youtube']), bytes)
        #vimeo
        for key in ['vimeo', 'vimeo_unlisted_video', 'vimeo_player', 'vimeo_player_unlisted_video']:
            self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls[key]), bytes)
        #dailymotion
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['dailymotion']), bytes)
        #instagram
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['instagram']), bytes)
        #default
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['youku']), bytes)
