# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.model
    def _get_compatible_providers(self, *args, website_id=None, **kwargs):
        """ Override of payment to only return providers matching website-specific criteria.

        In addition to the base criteria, the website must either not be set or be the same as the
        one provided in the kwargs.

        :param int website_id: The provided website, as a `website` id
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        providers = super()._get_compatible_providers(*args, website_id=website_id, **kwargs)
        if website_id:
            providers = providers.filtered(
                lambda p: not p.website_id or p.website_id.id == website_id
            )
        return providers
