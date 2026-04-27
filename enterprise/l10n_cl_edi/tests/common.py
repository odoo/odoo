# -*- coding: utf-8 -*-
import base64
import logging
import os

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tools import misc

_logger = logging.getLogger(__name__)


def _check_with_xsd_patch(xml_to_validate, xsd_fname, env, prefix=None):
    return True


def _is_valid_certificate(self):
    for certificate in self:
        certificate.is_valid = True


class TestL10nClEdiCommon(AccountEdiTestCommon):
    @classmethod
    @AccountEdiTestCommon.setup_country('cl')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'name': 'Blanco Martin & Asociados EIRL',
            'street': 'Apoquindo 6410',
            'city': 'Les Condes',
            'phone': '+1 (650) 691-3277 ',
            'l10n_cl_dte_service_provider': 'SIITEST',
            'l10n_cl_dte_resolution_number': 0,
            'l10n_cl_dte_resolution_date': '2019-10-20',
            'l10n_cl_dte_email': 'info@bmya.cl',
            'l10n_cl_sii_regional_office': 'ur_SaC',
            'l10n_cl_company_activity_ids': [(6, 0, [cls.env.ref('l10n_cl_edi.eco_new_acti_620200').id])],
            'extract_in_invoice_digitalization_mode': 'no_send',
            'tax_calculation_rounding_method': 'round_globally',
        })
        cls.company_data['company'].partner_id.write({
            'l10n_cl_sii_taxpayer_type': '1',
            'vat': 'CL762012243',
            'l10n_cl_activity_description': 'activity_test',
        })
        content = misc.file_open('certificate/tests/data/cert.pfx', mode="rb").read()
        cls.certificate = cls.env['certificate.certificate'].create({
            'name': 'CL Test certificate',
            'content': base64.b64encode(content),
            'pkcs12_password': 'example',
            'subject_serial_number': '23841194-7',
            'company_id': cls.company_data['company'].id,
        })
        cls.private_key_id = cls.certificate.private_key_id
        cls.company_data['company'].write({
            'l10n_cl_certificate_ids': [(4, cls.certificate.id)]
        })

        cls.partner_sii = cls.env['res.partner'].create({
            'name': 'Partner SII',
            'is_company': 1,
            'city': 'Pudahuel',
            'country_id': cls.env.ref('base.cl').id,
            'street': 'Puerto Test 102',
            'phone': '+562 0000 0000',
            'website': 'http://www.partner_sii.cl',
            'company_id': cls.company_data['company'].id,
            'l10n_cl_dte_email': 'partner@sii.cl',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_cl.it_RUT').id,
            'l10n_cl_sii_taxpayer_type': '1',
            'l10n_cl_activity_description': 'activity_test',
            'vat': '76086428-5',
        })

        cls.partner_anonimo = cls.env['res.partner'].create({
            'name': 'Consumidor Final Anonimo',
            'l10n_cl_sii_taxpayer_type': '3',
            'street': '',
            'street2': '',
            'country_id': cls.env.ref('base.cl').id,
            'vat': '66666666-6',
        })
        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Sale Journal Test',
            'type': 'sale',
            'code': 'INV2',
            'l10n_cl_point_of_sale_type': 'online',
            'l10n_latam_use_documents': True,
            'default_account_id': cls.env['account.account'].search([
                ('company_ids', '=', cls.company_data['company'].id), ('code', '=', '310115')]).id
        })
        caf_file_template = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'template', 'caf_file_template.xml')).read()

        caf34_file = caf_file_template.replace('<TD></TD>', '<TD>34</TD>').replace(
            '<RS>Blanco Martin Asociados EIRL</RS>', '<RS>Blanco Martin &amp; Asociados EIRL</RS>').replace(
            '<RSAPK><M>xBcfZfii8tMuKkuuWIYxz68CZg55jaPsQQVkGjqDl1b7osuKzJEHtS0M3PrnSF6DxwUxg2XjS0IOregtLf+FwQ==</M><E>Aw==</E></RSAPK>',
            '<RSAPK><M>bRGTU5RcHmh+CE55s/swgQylOygCFDgxGj0CKpMuvlXEI+z3jy3ekU9AOGenUvupl8iA+VaAjSiXo0yW/NrT7Q==</M><E>AQAB</E></RSAPK>')
        cls.caf_factura_afecta = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII7620122434221201910221946.xml',
            'caf_file': base64.b64encode(caf34_file.encode('utf-8')),
            'l10n_latam_document_type_id': cls.env.ref('l10n_cl.dc_y_f_dte').id,
            'status': 'in_use',
        })

        caf33_file = caf_file_template.replace('<TD></TD>', '<TD>33</TD>')
        cls.caf_33 = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII7620122433321201910221946.xml',
            'caf_file': base64.b64encode(caf33_file.encode('utf-8')),
            'l10n_latam_document_type_id': cls.env.ref('l10n_cl.dc_a_f_dte').id,
            'status': 'in_use',
        })

        caf39_file = caf_file_template.replace('<TD></TD>', '<TD>39</TD>').replace(
            '<RNG><D>001</D><H>100</H></RNG>', '<RNG><D>1</D><H>100</H></RNG>')
        cls.caf_39 = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII7620122433921201910221946.xml',
            'caf_file': base64.b64encode(caf39_file.encode('utf-8')),
            'l10n_latam_document_type_id': cls.env.ref('l10n_cl.dc_b_f_dte').id,
            'status': 'in_use',
        })

        caf56_file = caf_file_template.replace('<TD></TD>', '<TD>56</TD>').replace(
            '<RNG><D>001</D><H>100</H></RNG>', '<RNG><D>122</D><H>200</H></RNG>')
        cls.caf_56 = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII7620122435621201910221946.xml',
            'caf_file': base64.b64encode(caf56_file.encode('utf-8')),
            'l10n_latam_document_type_id': cls.env.ref('l10n_cl.dc_nd_f_dte').id,
            'status': 'in_use',
        })

        l10n_latam_document_type_110 = cls.env.ref('l10n_cl.dc_fe_dte')
        l10n_latam_document_type_110.write({'active': True})

        caf110_file = caf_file_template.replace('<TD></TD>', '<TD>110</TD>')
        cls.caf_110 = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII76201224311021201910221946.xml',
            'caf_file': base64.b64encode(caf110_file.encode('utf-8')),
            'l10n_latam_document_type_id': l10n_latam_document_type_110.id,
            'status': 'in_use',
        })

        caf34_254_file = caf_file_template.replace('<TD></TD>', '<TD>34</TD>').replace(
            '<RNG><D>001</D><H>100</H></RNG>', '<RNG><D>001</D><H>300</H></RNG>')
        cls.caf_34_254 = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII7620122432921201910221946.xml',
            'caf_file': base64.b64encode(caf34_254_file.encode('utf-8')),
            'l10n_latam_document_type_id': cls.env['l10n_latam.document.type'].search([
                ('code', '=', '34'),
                ('country_id.code', '=', 'CL')
            ]).id,
            'status': 'in_use',
        })

        caf33_301_file = caf_file_template.replace('<TD></TD>', '<TD>33</TD>').replace(
            '<RNG><D>001</D><H>100</H></RNG>', '<RNG><D>001</D><H>310</H></RNG>')
        cls.caf_33_301 = cls.env['l10n_cl.dte.caf'].sudo().create({
            'filename': 'FoliosSII7620122431921201910221946.xml',
            'caf_file': base64.b64encode(caf33_301_file.encode('utf-8')),
            'l10n_latam_document_type_id': cls.env['l10n_latam.document.type'].search([
                ('code', '=', '33'),
                ('country_id.code', '=', 'CL')
            ]).id,
            'status': 'in_use',
        })
