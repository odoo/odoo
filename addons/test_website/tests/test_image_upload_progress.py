# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestImageUploadProgress(odoo.tests.HttpCase):

    def test_01_image_upload_progress(self):
        self.start_tour("/test_image_progress", 'test_image_upload_progress', login="admin")
