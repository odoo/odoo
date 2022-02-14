# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged
from odoo.tools import misc
from pytz import timezone


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEsEdiTbaiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_es.account_chart_template_full', edi_format_ref='l10n_es_edi_tbai.edi_es_tbai'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime(year=2022, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====

        cls.certificate = cls.env['l10n_es_edi.certificate'].create({
            'content': base64.encodebytes(
                misc.file_open("l10n_es_edi_tbai/demo/certificates/sello_entidad_act.p12", 'rb').read()),
            'password': 'IZDesa2021',
        })

        cls.company_data['company'].write({
            'name': 'EUS Company',
            'country_id': cls.env.ref('base.es').id,
            'state_id': cls.env.ref('base.state_es_ss').id,  # TODO test all
            'l10n_es_tbai_certificate_id': cls.certificate.id,
            'vat': cls.env['l10n_es.edi.tbai.util']._random_vat(force_new=True),  # random VAT (so chain is new)
            'l10n_es_tbai_test_env': True,
            'l10n_es_tbai_tax_agency': 'gipuzkoa',  # TODO test all
        })

        # ==== Business ====

        cls.partner_a.write({
            'name': "&@àÁ$£€èêÈÊöÔÇç¡⅛™³",  # special characters should be escaped appropriately
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'zip': 93071,
        })

        cls.partner_b.write({
            'vat': 'ESF35999705',
        })

        cls.product_t = cls.env["product.product"].create(
            {"name": "Test product"})
        cls.partner_t = cls.env["res.partner"].create({"name": "Test partner", "vat": "ESF35999705"})

    @classmethod
    def _get_tax_by_xml_id(cls, trailing_xml_id):
        """ Helper to retrieve a tax easily.

        :param trailing_xml_id: The trailing tax's xml id.
        :return:                An account.tax record
        """
        return cls.env.ref(f'l10n_es.{cls.env.company.id}_account_tax_template_{trailing_xml_id}')

    @classmethod
    def create_invoice(cls, **kwargs):
        return cls.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-01-01',
            'date': '2022-01-01',
            **kwargs,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                **line_vals,
            }) for line_vals in kwargs.get('invoice_line_ids', [])],
        })
