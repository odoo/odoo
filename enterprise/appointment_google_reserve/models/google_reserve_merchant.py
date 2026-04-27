# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError
from ..tools.google_reserve_iap import GoogleReserveIAP

from werkzeug.urls import url_join


class GoogleReserveMerchant(models.Model):
    _name = "google.reserve.merchant"
    _description = "Google Reserve Merchant"
    _inherit = ['mail.thread.phone']

    def _default_website(self):
        # Should technically be in a website bridge.
        default_website_url = False
        if default_website := self.env.ref('website.default_website', raise_if_not_found=False):
            default_website_url = default_website.get_base_url()
            if default_website.homepage_url:
                default_website_url = url_join(default_website_url, default_website.homepage_url)

        return default_website_url

    name = fields.Char('Merchant Name', required=True, default=lambda self: self.env.company.name)
    appointment_type_ids = fields.One2many('appointment.type', 'google_reserve_merchant_id', 'Appointments')

    business_category = fields.Char('Business Category', required=True,
                           help="Used by Google to try to match your physical address to your business.")
    phone = fields.Char('Phone', default=lambda self: self.env.company.phone,
                        help="Used by Google to properly match merchants and partners, recommended.")
    website_url = fields.Char('Website URL', default=_default_website,
                              help="Used by Google to properly match merchants and partners, recommended.")
    location_id = fields.Many2one('res.partner', required=True, string="Address",
                                  default=lambda self: self.env.company.partner_id,
                                  help="Used by Google to try to match your physical address to your business.")

    @api.constrains('location_id')
    def _check_location(self):
        for merchant in self:
            if not all(merchant.location_id[field] for field in ['country_id', 'city', 'zip', 'street']):
                raise ValidationError(_('Google Reserve requires a complete address.'
                                        'Including a Country, a City, a Postal Code and a Street'))

    def write(self, vals):
        res = super().write(vals)
        for merchant in self:
            GoogleReserveIAP().update_merchant(merchant)

        return res

    @api.model
    def _google_reserve_upload_feed(self):
        google_reserve_iap = GoogleReserveIAP()

        merchants = self.env['google.reserve.merchant'].search([])
        google_reserve_iap.upload_availabilities_feed(merchants)

        appointments_pending_sync = self.env['appointment.type'].search([
            ('google_reserve_pending_sync', '=', True)
        ])
        if appointments_pending_sync:
            appointments_pending_sync.google_reserve_pending_sync = False

    def _get_google_reserve_iap_endpoint(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'appointment_google_reserve.google_reserve_iap_endpoint',
            'https://google-reserve.api.odoo.com'
        )
