# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestMedia(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_replace_media(self):
        SVG = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        self.env['html_editor.media'].create({
            'name': 'sample.svg',
            'public': True,
            'mimetype': 'image/svg+xml',
            'raw': SVG,
            'res_model': 'ir.ui.view',
            'media_type': 'image',
        })
        self.start_tour("/", 'test_replace_media', login="admin")

    def test_02_image_link(self):
        self.start_tour("/", 'test_image_link', login="admin")
