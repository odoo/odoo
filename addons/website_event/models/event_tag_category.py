# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import event, website


class EventTagCategory(event.EventTagCategory, website.WebsitePublishedMultiMixin):

    def _default_is_published(self):
        return True
