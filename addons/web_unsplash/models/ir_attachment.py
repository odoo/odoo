# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def copy(self, default=None):
        default = dict(default or {})
        if self.url:
            url_frags = self.url.split('/')
            if url_frags[1] == 'unsplash':
                url_frags[3] = uuid.uuid4().hex
                default['url'] = '/'.join(url_frags)
        return super().copy(default)
