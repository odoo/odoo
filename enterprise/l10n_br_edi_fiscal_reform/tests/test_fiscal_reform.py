# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from contextlib import contextmanager
from unittest import mock
from unittest.mock import patch

from odoo.addons.l10n_br_avatax.tests.test_br_avatax import TestAvalaraBrInvoiceCommon
from odoo.addons.l10n_br_avatax.models.account_external_tax_mixin import AccountExternalTaxMixinL10nBR
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAvalaraBrInvoiceFiscalReform(TestAvalaraBrInvoiceCommon):
    @contextmanager
    def _mocked_iap(self, expected_request_file, response):
        # TODO JOV: migrate this to _with_mocked_l10n_br_iap_request() in Odoo 19
        json_module = json

        def _mocked_l10n_br_iap_request(route, company, json=None):
            def replace_ignore(dict_to_replace):
                new_dict = {}
                for k, v in dict_to_replace.items():
                    if v == "___ignore___":
                        v = mock.ANY
                    new_dict[k] = v
                return new_dict

            with misc.file_open(f'{self.test_module}/tests/mocked_requests/{expected_request_file}', 'r') as f:
                expected_request = json_module.loads(f.read(), object_hook=replace_ignore)
                self.maxDiff = None
                self.assertEqual(
                    json,
                    expected_request,
                    "Expected request did not match actual request."
                )

            return response

        with patch(
           f'{AccountExternalTaxMixinL10nBR.__module__}.AccountExternalTaxMixinL10nBR._l10n_br_iap_request',
           autospec=True,
           side_effect=_mocked_l10n_br_iap_request
        ):
            yield

    def test_01_invoice_br_fiscal_reform(self):
        """Set all the new fields for the fiscal reform and verify if the generated request is correct."""
        invoice, response = self._create_invoice_01_and_expected_response()
        invoice.company_id.l10n_br_is_icbs = True
        invoice.l10n_br_presence = '2'

        invoice.invoice_line_ids.mapped('product_id').write({
            'l10n_br_customs_regime_id': self.env.ref('l10n_br_edi_fiscal_reform.customs_regime_capital_goods'),
            'l10n_br_legal_uom_id': self.env.ref('uom.product_uom_unit'),
        })
        self.product_user.write({
            'l10n_br_nbs_id': self.env.ref('l10n_br_edi_fiscal_reform.nbs_101'),
            'l10n_br_legal_uom_id': self.env.ref('uom.product_uom_dozen'),
        })

        invoice.partner_id.write({
            'l10n_br_tax_regime': 'simplified',
            'l10n_br_is_cbs_ibs_normal': False,
            'l10n_br_cbs_credit': 5,
            'l10n_br_ibs_credit': 10,
        })

        invoice.invoice_line_ids[0].l10n_br_cbs_ibs_deduction = 7

        with self._mocked_iap("fiscal_reform_request_goods.json", response):
            invoice.button_external_tax_calculation()

        # Test service invoice as well.
        invoice.partner_id.l10n_br_tax_regime = 'individual'
        invoice.partner_id.city_id = self.env['res.city'].create({
            'name': 'test',
            'country_id': self.env.ref('base.br').id
        })
        invoice.invoice_line_ids.mapped('product_id').write({
            'type': 'service',
            'l10n_br_property_service_code_origin_id': self.env['l10n_br.service.code'].create({
                'code': '123',
                'city_id': invoice.partner_id.city_id.id
            }).id
        })
        invoice.l10n_br_service_operation_indicator = '123'
        invoice.l10n_latam_document_type_id = self.env.ref('l10n_br.dt_SE')
        invoice.l10n_br_goods_operation_type_id = self.env.ref('l10n_br_edi_fiscal_reform.operation_type_sales_other_services_onerous')

        with self._mocked_iap("fiscal_reform_request_services.json", response):
            invoice.button_external_tax_calculation()
