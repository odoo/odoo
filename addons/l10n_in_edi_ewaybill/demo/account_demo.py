# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        if company and company.account_fiscal_country_id.code == 'IN':
            self._update_l10n_in_demo_data(company)
        return super()._post_load_demo_data(company)

    @api.model
    def _update_l10n_in_demo_data(self, company=False):
        indian_companies = company or self.env['res.company'].search([('account_fiscal_country_id.code', '=', 'IN')])
        for indian_company in indian_companies:
            if indian_company.state_id:
                invoices = [
                    'demo_invoice_b2b_1',
                    'demo_invoice_b2b_2',
                    'demo_invoice_b2cs',
                    'demo_invoice_b2cl',
                    'demo_invoice_nill',
                ]
                for xml_id in invoices:
                    self.ref("account.%s_%s"%(indian_company.id, xml_id)).write({
                        'l10n_in_type_id': self.env.ref("l10n_in_edi_ewaybill.type_tax_invoice_sub_type_supply"),
                        'l10n_in_distance': 20,
                        'l10n_in_mode': '1',
                        'l10n_in_vehicle_no': 'GJ11OD1234',
                        'l10n_in_vehicle_type': 'R',
                    })
            else:
                _logger.error('Error while loading Indian-Ewaybill demo data in the company "%s".State is not set in the company.', indian_company.name)
