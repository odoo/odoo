# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug

from odoo import models
from odoo.addons.mass_mailing_sms.models.sms_sms import TEXT_URL_REGEX


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    def _convert_links_text(self, body, vals, blacklist=None):
        shortened_schema = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/r/'
        unsubscribe_schema = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/sms/'
        for match in re.findall(TEXT_URL_REGEX, body):
            original_url = match[0]
            # don't shorten already-shortened links or links towards unsubscribe page
            if original_url.startswith(shortened_schema) or original_url.startswith(unsubscribe_schema):
                continue
            # support blacklist items in path, like /u/
            parsed = werkzeug.urls.url_parse(original_url, scheme='http')
            if blacklist and any(item in parsed.path for item in blacklist):
                continue

            vals['url'] = werkzeug.utils.unescape(original_url)
            link = self.create(vals)
            shortened_url = link.short_url
            if shortened_url:
                body = body.replace(original_url, shortened_url)

        return body
