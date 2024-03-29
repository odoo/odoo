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
        'dailymotion': 'https://www.dailymotion.com/video/x7svr6t',
        'youku': 'https://v.youku.com/v_show/id_XMzY1MjY4.html?spm=a2hzp.8244740.0.0',
        'instagram': 'https://www.instagram.com/p/B6dXGTxggTG/',
        'dailymotion_hub_no_video': 'http://www.dailymotion.com/hub/x9q_Galatasaray',
        'dailymotion_hub_#video': 'http://www.dailymotion.com/hub/x9q_Galatasaray#video=x2jvvep',
        'dai.ly': 'https://dai.ly/x578has',
        'dailymotion_embed': 'https://www.dailymotion.com/embed/video/x578has?autoplay=1',
        'dailymotion_video_extra': 'https://www.dailymotion.com/video/x2jvvep_hakan-yukur-klip_sport',
        'player_youku': 'https://player.youku.com/player.php/sid/XMTI5Mjg5NjE4MA==/v.swf',
        'youku_embed': 'https://player.youku.com/embed/XNTIwMzE1MzUzNg',
    }

    def test_player_regexes(self):
        #youtube
        self.assertIsNotNone(re.search(tools.player_regexes['youtube'], TestVideoUtils.urls['youtube']))
        #vimeo
        self.assertIsNotNone(re.search(tools.player_regexes['vimeo'], TestVideoUtils.urls['vimeo']))
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
        #youku
        self.assertEqual('youku', tools.get_video_source_data(TestVideoUtils.urls['youku'])[0])
        self.assertEqual('XMzY1MjY4', tools.get_video_source_data(TestVideoUtils.urls['youku'])[1])
        self.assertEqual('youku', tools.get_video_source_data(TestVideoUtils.urls['player_youku'])[0])
        self.assertEqual('XMTI5Mjg5NjE4MA', tools.get_video_source_data(TestVideoUtils.urls['player_youku'])[1])
        self.assertEqual('youku', tools.get_video_source_data(TestVideoUtils.urls['youku_embed'])[0])
        self.assertEqual('XNTIwMzE1MzUzNg', tools.get_video_source_data(TestVideoUtils.urls['youku_embed'])[1])
        #instagram
        self.assertEqual('instagram', tools.get_video_source_data(TestVideoUtils.urls['instagram'])[0])
        self.assertEqual('B6dXGTxggTG', tools.get_video_source_data(TestVideoUtils.urls['instagram'])[1])

    def test_get_video_url_data(self):
        self.assertEqual(4, len(tools.get_video_url_data(TestVideoUtils.urls['youtube'])))
        #youtube
        self.assertEqual('youtube', tools.get_video_url_data(TestVideoUtils.urls['youtube'])['platform'])
        #vimeo
        self.assertEqual('vimeo', tools.get_video_url_data(TestVideoUtils.urls['vimeo'])['platform'])
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
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['vimeo']), bytes)
        #dailymotion
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['dailymotion']), bytes)
        #instagram
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['instagram']), bytes)
        #default
        self.assertIsInstance(tools.get_video_thumbnail(TestVideoUtils.urls['youku']), bytes)
