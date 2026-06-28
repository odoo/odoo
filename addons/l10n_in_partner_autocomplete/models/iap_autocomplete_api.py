# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IapAutocompleteEnrichAPI(models.AbstractModel):
    _inherit = 'iap.autocomplete.api'

    @api.model
    def _request_partner_autocomplete(self, action, params, timeout=15):
        """ Add params that return GST Treatment.

        :return tuple: results, error code
        """
        params['get_in_gst_treatment'] = True
        return super()._request_partner_autocomplete(action, params, timeout)
