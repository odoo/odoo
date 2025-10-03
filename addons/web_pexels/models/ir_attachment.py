# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Attachment(models.Model):

    _inherit = "ir.attachment"

    def _can_bypass_rights_on_media_dialog(self, **attachment_data):
        # We need to allow and sudo the case of an "url + file" attachment,
        # which is by default forbidden for non admin.
        # See `_check_serving_attachments`
        forbidden = 'url' in attachment_data and attachment_data.get('type', 'binary') == 'binary'
        if forbidden and attachment_data['url'].startswith('/pexels/'):
            return True
        return super()._can_bypass_rights_on_media_dialog(**attachment_data)
