from odoo import api, fields, models
from odoo.addons.payment_razorpay.const import SUPPORTED_CURRENCIES as RAZORPAY_SUPPORTED_CURRENCIES


class ResCompany(models.Model):
    _inherit = 'res.company'

    razorpay_display_connect_button = fields.Boolean(compute='_compute_razorpay_display_connect_button')

    @api.depends('currency_id')
    def _compute_razorpay_display_connect_button(self):
        has_razorpay_support_per_company = {
            company.id: bool(count)
            for company,count in self.env['payment.provider'].read_group(
                [
                    *self.env['payment.provider']._check_company_domain(self),
                    ('code', '=', 'razorpay'),
                    ('currency_id.name', 'in', RAZORPAY_SUPPORTED_CURRENCIES),
                ],
                ['company_id'],
                ['__count'],
        )}
        for company in self:
            company.razorpay_display_connect_button = has_razorpay_support_per_company.get(company.id, False)
