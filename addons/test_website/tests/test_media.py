# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestMedia(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_replace_media(self):
        GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
        self.env['ir.attachment'].create({
            'name': 'sample.gif',
            'public': True,
            'mimetype': 'image/gif',
            'datas': GIF,
        })
        self.start_tour("/", 'test_replace_media', login="admin")
