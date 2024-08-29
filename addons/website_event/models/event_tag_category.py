# -*- coding: utf-8 -*-
from odoo.addons import event, website
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventTagCategory(models.Model, event.EventTagCategory, website.WebsitePublishedMultiMixin):

    def _default_is_published(self):
        return True
