# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _can_be_edited_by_current_partner(self, **kwargs):
        return super()._can_be_edited_by_current_partner(**kwargs) and not self.is_mondialrelay
