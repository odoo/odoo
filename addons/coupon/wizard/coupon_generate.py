# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

import ast
from odoo.osv import expression


class CouponGenerate(models.TransientModel):
    _name = 'coupon.generate.wizard'
    _description = 'Generate Coupon'

    nbr_coupons = fields.Integer(string="Number of Coupons", help="Number of coupons", default=1)
    generation_type = fields.Selection([
        ('nbr_coupon', 'Number of Coupons'),
        ('nbr_customer', 'Number of Selected Customers')
        ], default='nbr_coupon')
    partners_domain = fields.Char(string="Customer", default='[]')
    has_partner_email = fields.Boolean(compute='_compute_has_partner_email')

    def generate_coupon(self):
        """Generates the number of coupons entered in wizard field nbr_coupons
        """
        program = self.env['coupon.program'].browse(self.env.context.get('active_id'))

        vals = {'program_id': program.id}

        if self.generation_type == 'nbr_coupon' and self.nbr_coupons > 0:
            for count in range(0, self.nbr_coupons):
                self.env['coupon.coupon'].create(vals)

        if self.generation_type == 'nbr_customer' and self.partners_domain:
            for partner in self.env['res.partner'].search(ast.literal_eval(self.partners_domain)):
                vals.update({'partner_id': partner.id, 'state': 'sent' if partner.email else 'new'})
                coupon = self.env['coupon.coupon'].create(vals)
                context = dict(lang=partner.lang)
                subject = _('%s, a coupon has been generated for you') % (partner.name)
                del context
                template = self.env.ref('coupon.mail_template_sale_coupon', raise_if_not_found=False)
                if template:
                    email_values = {'email_from': self.env.user.email or '', 'subject': subject}
                    template.send_mail(coupon.id, email_values=email_values, notif_layout='mail.mail_notification_light')

    @api.depends('partners_domain')
    def _compute_has_partner_email(self):
        for record in self:
            domain = expression.AND([ast.literal_eval(record.partners_domain), [('email', '=', False)]])
            record.has_partner_email = self.env['res.partner'].search_count(domain) == 0
