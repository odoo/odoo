# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventTagCategory(models.Model):
    _inherit = ['event.tag.category', 'website.published.multi.mixin']

    def _default_is_published(self):
        return True
