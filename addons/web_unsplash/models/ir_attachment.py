# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models


class Attachment(models.Model):

    _inherit = "ir.attachment"

    def _get_serve_attachment(self, url, extra_domain=None, order=None):
        # Bypass the default IrAttachment._search() behavior which adds
        # ('res_field', '=', False) to the domain if no `res_field` nor `id` is
        # set in the domain, as we at least want to fetch ('res_field', 'in',
        # (False, 'media_content')) when serving paths like
        # `/unsplash/<unsplash_id>/<name>.<ext>`. We add a meaningless id domain
        # in case some other module would have a legitimate 'res_field' query.
        if re.match(r'^/unsplash/[A-Za-z0-9-_]{11}/', url):
            extra_domain = (extra_domain or []) + [('id', '!=', False)]
        return super()._get_serve_attachment(url, extra_domain, order)
