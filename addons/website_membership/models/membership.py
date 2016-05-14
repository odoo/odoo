# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MembershipMembershipLine(models.Model):
    _inherit = 'membership.membership_line'

    def get_published_companies(self, limit=None):
        if not self.exists():
            return []
        return self.mapped('partner').filtered(lambda partner: partner.website_published and partner.is_company).ids[:limit]
