# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.web_editor.controllers.main import Web_Editor
from odoo.addons.web_unsplash.controllers.main import Web_Unsplash

import odoo.tests

from odoo import http


@odoo.tests.common.tagged('post_install', '-at_install')
class TestImageUploadProgress(odoo.tests.HttpCase):

    def test_01_image_upload_progress(self):
        self.start_tour("/web", 'test_image_upload_progress', login="admin")

    def test_02_image_upload_progress_unsplash(self):
        BASE_URL = self.base_url()

        def media_library_search(self, **params):
            return {"results": 0, "media": []}

        def fetch_unsplash_images(self, **post):
            return {
                'total': 1434,
                'total_pages': 48,
                'results': [{
                    'id': 'HQqIOc8oYro',
                    'alt_description': 'brown fox sitting on green grass field during daytime',
                    'urls': {
                        # 'regular': 'https://images.unsplash.com/photo-1462953491269-9aff00919695?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwzMDUwOHwwfDF8c2VhcmNofDF8fGZveHxlbnwwfHx8fDE2MzEwMzIzNDE&ixlib=rb-1.2.1&q=80&w=1080',
                        'regular': BASE_URL + '/website/static/src/img/phone.png',
                    },
                    'links': {
                        # 'download_location': 'https://api.unsplash.com/photos/HQqIOc8oYro/download?ixid=MnwzMDUwOHwwfDF8c2VhcmNofDF8fGZveHxlbnwwfHx8fDE2MzEwMzIzNDE'
                        'download_location': BASE_URL + '/website/static/src/img/phone.png',
                    },
                    'user': {
                        'name': 'Mitchell Admin',
                        'links': {
                            'html': BASE_URL,
                        },
                    },
                }]
            }

        # because not preprocessed by ControllerType metaclass
        fetch_unsplash_images.routing_type = 'json'
        Web_Unsplash.fetch_unsplash_images = http.route("/web_unsplash/fetch_images", type='json', auth="user")(fetch_unsplash_images)

        # disable undraw, no third party should be called in tests
        media_library_search.routing_type = 'json'
        Web_Editor.media_library_search = http.route(['/web_editor/media_library_search'], type='json', auth="user", website=True)(media_library_search)

        self.start_tour("/web", 'test_image_upload_progress_unsplash', login="admin")
