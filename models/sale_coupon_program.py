# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class SaleCouponProgram(models.Model):
    _inherit = 'sale.coupon.program'

    def _filter_programs_on_partners(self, order):
        return self.filtered(lambda program:
            program.with_context(active_test=False).rule_partner_ids and
            order.partner_id.id in program.with_context(active_test=False).rule_partner_ids.ids or
            not program.with_context(active_test=False).rule_partner_ids)
