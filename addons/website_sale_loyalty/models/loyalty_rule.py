# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    website_id = fields.Many2one(related='program_id.website_id', store=True)

    # NOTE: is this sufficient?
    @api.constrains('code', 'website_id', 'active')
    def _constrains_code(self):
        #Programs with the same code are allowed to coexist as long
        # as they are not both accessible from a website.
        with_code = self.filtered(lambda r: r.mode == 'with_code' and r.active)
        mapped_codes = with_code.mapped('code')
        read_result = self.env['loyalty.rule'].search_read(
            [('website_id', 'in', [False] + [w.id for w in self.website_id]),
            ('mode', '=', 'with_code'),
            ('code', 'in', mapped_codes),
            ('id', 'not in', with_code.ids),
            ('active', '=', True)],
            fields=['code', 'website_id']) + [{'code': p.code, 'website_id': p.website_id} for p in with_code]
        existing_codes = set()
        for res in read_result:
            website_checks = (res['website_id'], False) if res['website_id'] else (False,)
            for website in website_checks:
                val = (res['code'], website)
                if val in existing_codes:
                    raise ValidationError(_('The promo code must be unique.'))
                existing_codes.add(val)
        # Prevent coupons and programs from sharing a code
        if self.env['loyalty.card'].search_count([
            ('code', 'in', mapped_codes), ('active', '=', True)
        ]):
            raise ValidationError(_('A coupon with the same code was found.'))
