# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests
from odoo.tests.common import HOST
from odoo.tools import config


@odoo.tests.common.tagged('post_install', '-at_install', 'website_snippets')
class TestSnippets(odoo.tests.HttpCase):

    def test_01_empty_parents_autoremove(self):
        self.start_tour("/?enable_editor=1", "snippet_empty_parent_autoremove", login='admin')

    def test_02_countdown_preview(self):
        self.start_tour("/?enable_editor=1", "snippet_countdown", login='admin')

    def test_03_snippet_image_gallery(self):
        IrAttachment = self.env['ir.attachment']
        base = "http://%s:%s" % (HOST, config['http_port'])
        IrAttachment.create({
            'public': True,
            'name': 's_default_image.jpg',
            'type': 'url',
            'url': base + '/web/image/website.s_banner_default_image.jpg',
        })
        IrAttachment.create({
            'public': True,
            'name': 's_default_image2.jpg',
            'type': 'url',
            'url': base + '/web/image/website.s_banner_default_image.jpg',
        })
        self.start_tour("/", "snippet_image_gallery", login='admin')

    def test_04_parallax(self):
        self.start_tour('/', 'test_parallax', login='admin')
