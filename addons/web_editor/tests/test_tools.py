# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tests import common, tagged
from odoo.addons.web_editor import tools


@tagged('post_install', '-at_install')
class TestVideoUtils(common.BaseCase):
    urls = {
        'youtube': 'https://www.youtube.com/watch?v=xCvFZrrQq7k',
        'youtube_shorts_video': 'https://www.youtube.com/shorts/qAgW3oG7Zmc',
        'youtube_live_stream': 'https://www.youtube.com/live/fmVNEoxr7iU?feature=shared',
        'youtube_mobile': 'https://m.youtube.com/watch?v=xCvFZrrQq7k',
        'vimeo': 'https://vimeo.com/395399735',
        'vimeo_unlisted_video': 'https://vimeo.com/795669787/0763fdb816',
        'vimeo_player': 'https://player.vimeo.com/video/395399735',
        'vimeo_player_unlisted_video': 'https://player.vimeo.com/video/795669787?h=0763fdb816',
        'dailymotion': 'https://www.dailymotion.com/video/x7svr6t',
        'instagram': 'https://www.instagram.com/p/B6dXGTxggTG/',
        'dailymotion_hub_no_video': 'http://www.dailymotion.com/hub/x9q_Galatasaray',
        'dailymotion_hub_#video': 'http://www.dailymotion.com/hub/x9q_Galatasaray#video=x2jvvep',
        'dai.ly': 'https://dai.ly/x578has',
        'dailymotion_embed': 'https://www.dailymotion.com/embed/video/x578has?autoplay=1',
        'dailymotion_video_extra': 'https://www.dailymotion.com/video/x2jvvep_hakan-yukur-klip_sport',
    }

    def test_player_regexes(self):
        #youtube
        self.assertIsNotNone(re.search(tools.player_regexes['youtube'], TestVideoUtils.urls['youtube']))
        self.assertIsNotNone(re.search(tools.player_regexes['youtube'], TestVideoUtils.urls['youtube_shorts_video']))
        self.assertIsNotNone(re.search(tools.player_regexes['youtube'], TestVideoUtils.urls['youtube_live_stream']))
        #vimeo
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo'], TestVideoUtils.urls['vimeo']))
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo'], TestVideoUtils.urls['vimeo_unlisted_video']))
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo_player'], TestVideoUtils.urls['vimeo_player']))
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo_player'], TestVideoUtils.urls['vimeo_player_unlisted_video']))
        #dailymotion
        self.assertIsNotNone(re.search(tools.player_regexes['dailymotion'], TestVideoUtils.urls['dailymotion']))
        #instagram
        self.assertIsNotNone(re.search(tools.player_regexes['instagram'], TestVideoUtils.urls['instagram']))

    def test_get_video_source_data(self):
        self.assertEqual(3, len(tools.get_video_source_data(TestVideoUtils.urls['youtube'])))
        #youtube
        self.assertEqual('youtube', tools.get_video_source_data(TestVideoUtils.urls['youtube'])[0])
        self.assertEqual('xCvFZrrQq7k', tools.get_video_source_data(TestVideoUtils.urls['youtube'])[1])
        self.assertEqual('youtube', tools.get_video_source_data(TestVideoUtils.urls['youtube_shorts_video'])[0])
        self.assertEqual('qAgW3oG7Zmc', tools.get_video_source_data(TestVideoUtils.urls['youtube_shorts_video'])[1])
        self.assertEqual('youtube', tools.get_video_source_data(TestVideoUtils.urls['youtube_live_stream'])[0])
        self.assertEqual('fmVNEoxr7iU', tools.get_video_source_data(TestVideoUtils.urls['youtube_live_stream'])[1])
        self.assertEqual('youtube', tools.get_video_source_data(TestVideoUtils.urls['youtube_mobile'])[0])
        self.assertEqual('xCvFZrrQq7k', tools.get_video_source_data(TestVideoUtils.urls['youtube_mobile'])[1])
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
        self.assertEqual(None, tools.get_video_source_data(TestVideoUtils.urls['dailymotion_hub_no_video']))
        self.assertEqual('dailymotion', tools.get_video_source_data(TestVideoUtils.urls['dailymotion_hub_#video'])[0])
        self.assertEqual('x2jvvep', tools.get_video_source_data(TestVideoUtils.urls['dailymotion_hub_#video'])[1])
        self.assertEqual('dailymotion', tools.get_video_source_data(TestVideoUtils.urls['dai.ly'])[0])
        self.assertEqual('x578has', tools.get_video_source_data(TestVideoUtils.urls['dai.ly'])[1])
        self.assertEqual('dailymotion', tools.get_video_source_data(TestVideoUtils.urls['dailymotion_embed'])[0])
        self.assertEqual('x578has', tools.get_video_source_data(TestVideoUtils.urls['dailymotion_embed'])[1])
        self.assertEqual('dailymotion', tools.get_video_source_data(TestVideoUtils.urls['dailymotion_video_extra'])[0])
        self.assertEqual('x2jvvep', tools.get_video_source_data(TestVideoUtils.urls['dailymotion_video_extra'])[1])
        #instagram
        self.assertEqual('instagram', tools.get_video_source_data(TestVideoUtils.urls['instagram'])[0])
        self.assertEqual('B6dXGTxggTG', tools.get_video_source_data(TestVideoUtils.urls['instagram'])[1])

    def test_get_video_url_data(self):
        self.assertEqual(4, len(tools.get_video_url_data(TestVideoUtils.urls['youtube'])))
        #youtube
        for key in ['youtube', 'youtube_shorts_video', 'youtube_live_stream']:
            self.assertEqual('youtube', tools.get_video_url_data(TestVideoUtils.urls[key])['platform'])
        #vimeo
        for key in ['vimeo', 'vimeo_player']:
            self.assertEqual(tools.get_video_url_data(TestVideoUtils.urls[key]), {
                'platform': 'vimeo',
                'embed_url': '//player.vimeo.com/video/395399735?autoplay=0&dnt=1',
                'video_id': '395399735',
                'params': {
                    'autoplay': 0,
                    'dnt': 1,
                }
            })
        for key in ['vimeo_unlisted_video', 'vimeo_player_unlisted_video']:
            self.assertEqual(tools.get_video_url_data(TestVideoUtils.urls[key]), {
                'platform': 'vimeo',
                'embed_url': '//player.vimeo.com/video/795669787?autoplay=0&dnt=1&h=0763fdb816',
                'video_id': '795669787',
                'params': {
                    'autoplay': 0,
                    'dnt': 1,
                    'h': '0763fdb816',
                }
            })
        #dailymotion
        self.assertEqual('dailymotion', tools.get_video_url_data(TestVideoUtils.urls['dailymotion'])['platform'])
        #instagram
        self.assertEqual('instagram', tools.get_video_url_data(TestVideoUtils.urls['instagram'])['platform'])

    def test_valid_video_url(self):
        self.assertIsNotNone(re.search(tools.valid_url_regex, TestVideoUtils.urls['youtube']))


@tagged('-standard', 'external')
class TestVideoUtilsExternal(common.BaseCase):
    def test_get_video_thumbnail(self):
        #youtube
        for key in ['youtube', 'youtube_shorts_video', 'youtube_live_stream']:
            self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls[key]), bytes)
        #vimeo
        for key in ['vimeo', 'vimeo_unlisted_video', 'vimeo_player', 'vimeo_player_unlisted_video']:
            self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls[key]), bytes)
        #dailymotion
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['dailymotion']), bytes)
        #instagram
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['instagram']), bytes)
