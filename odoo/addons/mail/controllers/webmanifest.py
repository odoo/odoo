# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.tools import file_open
from odoo.addons.web.controllers.webmanifest import WebManifest as WebWebManifest


class WebManifest(WebWebManifest):

    def _get_service_worker_content(self):
        body = super()._get_service_worker_content()

        # Add notification support to the service worker if user but no public
        if request.env.user.has_group('base.group_user'):
            with file_open('mail/static/src/service_worker.js') as f:
                body += f.read()

        return body
