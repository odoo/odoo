# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.exceptions import UserError
from odoo import _

class ItalyWebsiteSaleForm(WebsiteSale):
    def checkout_form_validate(self, mode, all_form_values, data):
        error, error_message = super().checkout_form_validate(mode, all_form_values, data)
        Partner = request.env['res.partner']
        if data.get('l10n_it_codice_fiscale'):
            partner_dummy = Partner.new({
                'l10n_it_codice_fiscale': data.get('l10n_it_codice_fiscale')
            })
            try:
                partner_dummy.validate_codice_fiscale()
            except UserError as e:
                error['l10n_it_codice_fiscale'] = 'error'
                error_message.append(e.name)
        pa_index = data.get('l10n_it_pa_index')
        if pa_index:
            if len(pa_index) < 6 or len(pa_index) > 7:
                error['l10n_it_pa_index'] = 'error'
                error_message.append(_('Destination Code (SDI) must have between 6 and 7 characters'))
        return error, error_message
