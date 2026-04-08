# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.web.controllers import webmanifest


class WebManifest(webmanifest.WebManifest):

    def _has_share_target(self):
        return True
