# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    website_id = fields.Many2one(related='program_id.website_id', store=True)

    # NOTE: is this sufficient?
    @api.constrains('code', 'website_id')
    def _constrains_code(self):
        #Programs with the same code are allowed to coexist as long
        # as they are not both accessible from a website.
        with_code = self.filtered(lambda r: r.mode == 'with_code')
        mapped_codes = with_code.mapped('code')
        domain = [
            ('mode', '=', 'with_code'), ('code', 'in', mapped_codes), ('id', 'not in', self.ids)
        ]
        if self.website_id:
            domain.append(('website_id', 'in', [False] + [w.id for w in self.website_id]))
        if (
            len(mapped_codes) != len(set(mapped_codes))
            or self.env['loyalty.rule'].search_count(domain)
        ):
            raise ValidationError(_('The promo code must be unique.'))
        # Prevent coupons and programs from sharing a code
        if self.env['loyalty.card'].search_count([('code', 'in', mapped_codes)]):
            raise ValidationError(_('A coupon with the same code was found.'))
