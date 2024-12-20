# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _can_edited_by_current_customer(self, **kwargs):
        return not self.is_mondialrelay and super()._can_edited_by_current_customer(**kwargs)
