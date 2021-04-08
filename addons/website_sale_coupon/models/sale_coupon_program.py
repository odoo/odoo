# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class CouponProgram(models.Model):
    _name = 'coupon.program'
    _inherit = ['coupon.program', 'website.multi.mixin']

    @api.constrains('promo_code', 'website_id')
    def _check_promo_code_constraint(self):
        """ Only case where multiple same code could coexists is if they all belong to their own website.
            If the program is website generic, we should ensure there is no generic and no specific (even for other website) already
            If the program is website specific, we should ensure there is no existing code for this website or False
        """
        for program in self.filtered(lambda p: p.promo_code):
            domain = [('id', '!=', program.id), ('promo_code', '=', program.promo_code)]
            if program.website_id:
                domain += program.website_id.website_domain()
            if self.search(domain):
                raise ValidationError(_('The program code must be unique by website!'))

    def _filter_programs_on_website(self, order):
        return self.filtered(lambda program: not program.website_id or program.website_id.id == order.website_id.id)

    @api.model
    def _filter_programs_from_common_rules(self, order, next_order=False):
        programs = self._filter_programs_on_website(order)
        return super(CouponProgram, programs)._filter_programs_from_common_rules(order, next_order)

    def _check_promo_code(self, order, coupon_code):
        if self.website_id and self.website_id != order.website_id:
            return {'error': 'This promo code is not valid on this website.'}
        return super()._check_promo_code(order, coupon_code)

    def action_program_share(self):
        """ Open a window to copy the program link """
        self.ensure_one()
        return self.env['coupon.share'].create_share_action(program=self)
