# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import BinaryBytes, file_open


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        worldline_providers = providers.filtered(lambda provider: provider.code == 'worldline')
        worldline_providers._apply_worldline_branding()
        return providers

    @api.model
    def _load_image_binary(self, image_path):
        try:
            with file_open(image_path, 'rb', filter_ext=('.png',)) as image_file:
                return BinaryBytes(image_file.read())
        except (FileNotFoundError, ValueError):
            return False

    def _apply_worldline_branding(self):
        fr_providers = self.filtered(lambda provider: provider.company_id.is_france_country)
        non_fr_providers = self - fr_providers
        if fr_providers:
            fr_providers._apply_fr_worldline_branding()
        if non_fr_providers:
            non_fr_providers._apply_default_worldline_branding()

    def _apply_default_worldline_branding(self):
        default_image = self._load_image_binary('payment_worldline/static/description/icon.png')
        values = {'name': 'Worldline'}
        if default_image:
            values['image_128'] = default_image
        self.sudo().write(values)

    def _apply_fr_worldline_branding(self):
        fr_image = self._load_image_binary('l10n_fr_payment/static/description/worldline_cawl.png')
        values = {'name': 'CAWL (Worldline)'}
        if fr_image:
            values['image_128'] = fr_image
        self.sudo().write(values)
