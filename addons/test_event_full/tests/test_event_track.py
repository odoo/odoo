# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_event_full.tests.common import TestWEventCommon
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestEventTrack(TestWEventCommon):

    def test_event_track(self):
        self.track_0['duration'] = 200
        self.start_tour('/event/%s' % slug(self.event), 'event_track')
