# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import event, website


class EventTag(event.EventTag, website.WebsitePublishedMultiMixin):

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('default_website_id'):
            result['website_id'] = self.env.context.get('default_website_id')
        return result
