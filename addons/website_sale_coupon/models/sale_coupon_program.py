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
