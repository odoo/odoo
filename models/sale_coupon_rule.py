# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

class SaleCouponRule(models.Model):
    _inherit = "sale.coupon.rule"

    is_public_included = fields.Boolean(string="Include Public User", help="Is the public user included into the set of autorized customers", default=True)

    @api.depends('is_public_included')
    def _compute_rule_partner_ids(self):
        for applicability in self.filtered(lambda x: x.rule_partners_domain):
            domain = safe_eval(applicability.rule_partners_domain)
            applicability.rule_partner_ids = domain and self.env['res.partner'].search(domain)
            if self.is_public_included:
                public_users = self.sudo().env.ref('base.group_public').with_context(active_test=False).users
                public_partners = public_users.mapped('partner_id')
                applicability.rule_partner_ids += public_partners
