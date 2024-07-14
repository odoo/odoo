# -*- coding: utf-8 -*-
import base64

from odoo import fields, Command
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon

from odoo.tools import misc, relativedelta


class TestL10nClEdiStockCommon(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref='cl')

        cls.env.company.write({
            'country_id': cls.env.ref('base.cl').id,
            'name': 'Blanco Martin & Asociados EIRL',
            'street': 'Apoquindo 6410',
            'city': 'Les Condes',
            'phone': '+1 (650) 691-3277 ',
            'l10n_cl_dte_service_provider': 'SIITEST',
            'l10n_cl_dte_resolution_number': 0,
            'l10n_cl_dte_resolution_date': '2019-10-20',
            'l10n_cl_dte_email': 'info@bmya.cl',
            'l10n_cl_sii_regional_office': 'ur_SaC',
            'l10n_cl_company_activity_ids': [Command.set(cls.env.ref('l10n_cl_edi.eco_new_acti_620200').ids)],
            'extract_in_invoice_digitalization_mode': 'no_send',
        })

        cls.env.company.partner_id.write({
            'l10n_cl_sii_taxpayer_type': '1',
            'vat': 'CL762012243',
            'l10n_cl_activity_description': 'activity_test',
        })
        cls.warehouse = cls.company_data['default_warehouse']
        cls.customer_location = cls.env.ref('stock.stock_location_customers').id
        cls.stock_location = cls.warehouse.lot_stock_id.id
        cls.chilean_partner_a = cls.env['res.partner'].create({
            'name': 'Chilean Partner A',
            'is_company': 1,
            'city': 'Pudahuel',
            'country_id': cls.env.ref('base.cl').id,
            'street': 'Puerto Test 102',
            'phone': '+562 0000 0000',
            'company_id': cls.env.company.id,
            'l10n_cl_dte_email': 'chilean.partner.a@example.com',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_cl.it_RUT').id,
            'l10n_cl_sii_taxpayer_type': '1',
            'l10n_cl_activity_description': 'activity_test',
            'vat': '76086428-5',
            'l10n_cl_delivery_guide_price': 'sale_order',
        })

        cls.certificate = cls.env['l10n_cl.certificate'].sudo().create({
            'signature_filename': 'Test',
            'subject_serial_number': '23841194-7',
            'signature_pass_phrase': 'asadadad',
            'private_key': misc.file_open('l10n_cl_edi_stock/tests/private_key_test.key').read(),
            'certificate': misc.file_open('l10n_cl_edi_stock/tests/cert_test.cert').read(),
            'cert_expiration': fields.Datetime.now() + relativedelta(years=1),
            'company_id': cls.env.company.id
        })
        cls.env.company.write({
            'l10n_cl_certificate_ids': [(4, cls.certificate.id)]
        })
        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'IVA 19% Venta',
            'type_tax_use': 'sale',
            'amount': 19.0,
            'company_id': cls.env.company.id,
            'l10n_cl_sii_code': 14,
        })
        cls.tax_10 = cls.env['account.tax'].create({
            'name': 'Beb. Analc. 10% (Ventas)',
            'type_tax_use': 'sale',
            'amount': 10.0,
            'company_id': cls.env.company.id,
            'l10n_cl_sii_code': 27,
        })
        cls.env.ref('uom.product_uom_unit').name = 'U'
        cls.product_with_taxes_a = cls.env['product.product'].create({
            'name': 'Tapa Ranurada UL FM 300 6"',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'type': 'product',
            'list_price': 172050.0,
            'taxes_id': [(6, 0, [cls.tax_19.id])]
        })
        cls.product_with_taxes_b = cls.env['product.product'].create({
            'name': 'Copla Flexible 1NS 6"',
            'type': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'list_price': 51240.0,
            'taxes_id': [(6, 0, [cls.tax_19.id])]
        })
        cls.product_without_taxes_a = cls.env['product.product'].create({
            'name': 'Tapa Ranurada',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'type': 'product',
            'list_price': 10000.0,
            'taxes_id': [],
        })
        cls.product_without_taxes_b = cls.env['product.product'].create({
            'name': 'Copla Flexible 1NS 5.3"',
            'type': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'list_price': 2500.0,
            'taxes_id': [],
        })

        l10n_latam_document_type_52 = cls.env.ref('l10n_cl.dc_gd_dte')
        l10n_latam_document_type_52.write({'active': True})

        caf_file_template = misc.file_open('l10n_cl_edi_stock/tests/template/caf_file_template.xml').read()

        caf52_file = caf_file_template.replace('<TD></TD>', '<TD>52</TD>')
        cls.caf52_file = cls.env['l10n_cl.dte.caf'].with_company(cls.env.company.id).sudo().create({
            'filename': 'FoliosSII7620122435221201910221946.xml',
            'caf_file': base64.b64encode(caf52_file.encode('utf-8')),
            'l10n_latam_document_type_id': l10n_latam_document_type_52.id,
            'status': 'in_use',
        })

        cls.env['product.pricelist'].search([]).unlink()
