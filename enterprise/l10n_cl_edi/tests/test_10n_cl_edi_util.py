# -*- coding: utf-8 -*-
import os

from lxml import etree
from unittest.mock import patch

from odoo import fields
from odoo.tools import misc
from odoo.tests.common import tagged
from .common import TestL10nClEdiCommon, _check_with_xsd_patch, _is_valid_certificate


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
@tagged('post_install', '-at_install')
class TestL10nClDte(TestL10nClEdiCommon):
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed_ws')
    def test_get_seed_none(self, get_seed_ws):
        get_seed_ws.return_value = None
        with self.assertRaises(Exception):
            self.env['l10n_cl.edi.util']._get_seed('SIITEST')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed_ws')
    def test_get_seed_ok(self, get_seed_ws):
        get_seed_ws.return_value = (
            """<?xml version="1.0" encoding="UTF-8" ?>
               <SII:RESPUESTA xmlns:SII="http://www.sii.cl/xxx">
                <SII:RESP_HDR>
                    <ESTADO>00</ESTADO>
                </SII:RESP_HDR>
                <SII:RESP_BODY>
                    <SEMILLA>00000000064</SEMILLA>
                </SII:RESP_BODY>
               </SII:RESPUESTA>""")

        self.assertEqual(self.env['l10n_cl.edi.util']._get_seed('SIITEST'), '00000000064')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed_ws')
    def test_get_seed_no_seed_exception(self, get_seed_ws):
        get_seed_ws.return_value = (
            """<?xml version="1.0" encoding="UTF-8" ?>
                <SII:RESPUESTA xmlns:SII="http://www.sii.cl/xxx">
                    <SII:RESP_HDR>
                        <ESTADO>-1</ESTADO>
                        <GLOSA>Error : (Message Exception) </GLOSA>
                    </SII:RESP_HDR>
                </SII:RESPUESTA>""")

        with self.assertRaises(Exception):
            self.env['l10n_cl.edi.util']._get_seed('SIITEST')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed_ws')
    def test_get_seed_retorno_error_exception(self, get_seed_ws):
        get_seed_ws.return_value = (
            """<?xml version="1.0" encoding="UTF-8" ?>
                    <SII:RESPUESTA xmlns:SII="http://www.sii.cl/xxx">
                        <SII:RESP_HDR>
                            <ESTADO>-2</ESTADO>
                            <GLOSA>ERROR RETORNO</GLOSA>
                        </SII:RESP_HDR>
                    </SII:RESPUESTA>""")

        with self.assertRaises(Exception):
            self.env['l10n_cl.edi.util']._get_seed('SIITEST')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.Client')
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_signed_token')
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed_ws')
    def get_token_none_error(self, get_seed_ws, get_signed_token, mock_client):
        get_seed_ws.return_value = '1234456'
        get_signed_token.return_value = 'test'
        mock_client.return_value.service.getToken.return_value = b'<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html><head>\n<title>503 Service Temporarily Unavailable</title>\n</head><body>\n<h1>Service Temporarily Unavailable</h1>\n<p>The server is temporarily unable to service your\nrequest due to maintenance downtime or capacity\nproblems. Please try again later.</p>\n</body></html>\n'
        with self.assertRaises(Exception):
            self.env['l10n_cl.edi.util']._get_seed('SIITEST', '', '')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.Client')
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_signed_token')
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed')
    def get_token_certificate_no_exists(self, get_seed, get_signed_token, mock_client):
        get_seed.return_value = '1234456'
        get_signed_token.return_value = 'test'
        mock_client.return_value.service.getToken.return_value = (
            """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/xxx">
                <SII:RESP_HDR>
                    <ESTADO>11</ESTADO>
                    <GLOSA>XML Invalido, elemento “Certificate” no existe, función getCertificado</GLOSA>
                </SII:RESP_HDR>
            </SII:RESPUESTA>""")
        with self.assertRaises(Exception):
            self.env['l10n_cl.edi.util']._get_seed('SIITEST', '', '')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.Client')
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_signed_token')
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_seed')
    def get_token_rut_validation_error(self, get_seed, get_signed_token, mock_client):
        get_seed.return_value = '1234456'
        get_signed_token.return_value = 'test'
        mock_client.return_value.service.getToken.return_value = (
            """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/xxx">
                <SII:RESP_HDR>
                    <ESTADO>12</ESTADO>
                    <GLOSA>ERROR (12) (MessageException)</GLOSA>
                </SII:RESP_HDR>
            </SII:RESPUESTA>""")
        with self.assertRaises(Exception):
            self.env['l10n_cl.edi.util']._get_seed('SIITEST', '', '')

    @patch('odoo.addons.certificate.models.certificate.Certificate._compute_is_valid', _is_valid_certificate)
    def test_get_token_ok(self):
        seed = '023071972740'
        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_xml', 'token.xml')).read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env['l10n_cl.edi.util']._get_signed_token(self.certificate, seed).encode()),
            self.get_xml_tree_from_string(xml_expected_dte.encode())
        )

    def test_analyze_sii_result_rsc(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
        <ESTADO>RSC</ESTADO>
        <GLOSA>Rechazado por Error en Schema</GLOSA>
         <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'rejected')

    def test_analyze_sii_result_sok(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>SDK</ESTADO>
            <GLOSA >Schema Validado</GLOSA >
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'ask_for_status')

    def test_analyze_sii_result_crt(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>CRT</ESTADO>
            <GLOSA >Caratula OK</GLOSA>
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'ask_for_status')

    def test_analyze_sii_result_rfr(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>RFR</ESTADO>
            <GLOSA>Rechazado por Error en Firma</GLOSA>
             <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'rejected')

    def test_analyze_sii_result_fok(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>05</ESTADO>
            <GLOSA>Error: RETORNO DATOS</GLOSA>
             <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'rejected')

    def test_analyze_sii_result_prd(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>PRD</ESTADO>
            <GLOSA>Error Retorno Datos</GLOSA>
             <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
            </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'rejected')

    def test_analyze_sii_result_rct(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>RCT</ESTADO>
            <GLOSA>Rechazado por Error en Carátula</GLOSA>
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'rejected')

    def test_analyze_sii_result_epr_accepted(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
        <TRACKID>251</TRACKID>
        <ESTADO>EPR</ESTADO>
        <GLOSA>Envio Procesado</GLOSA>
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        <SII:RESP_BODY>
            <TIPO_DOCTO>33</TIPO_DOCTO>
            <INFORMADOS>1</INFORMADOS>
            <ACEPTADOS>1</ACEPTADOS>
            <RECHAZADOS>0</RECHAZADOS>
            <REPAROS>0</REPAROS>
        </SII:RESP_BODY>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'accepted')

    def test_analyze_sii_result_epr_rejected(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
        <TRACKID>251</TRACKID>
        <ESTADO>EPR</ESTADO>
        <GLOSA>Envio Procesado</GLOSA>
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        <SII:RESP_BODY>
            <TIPO_DOCTO>33</TIPO_DOCTO>
            <INFORMADOS>1</INFORMADOS>
            <ACEPTADOS>0</ACEPTADOS>
            <RECHAZADOS>1</RECHAZADOS>
            <REPAROS>0</REPAROS>
        </SII:RESP_BODY>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'rejected')

    def test_analyze_sii_result_objected(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
        <TRACKID>251</TRACKID>
        <ESTADO>EPR</ESTADO>
        <GLOSA>Envio Procesado</GLOSA>
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        <SII:RESP_BODY>
            <TIPO_DOCTO>33</TIPO_DOCTO>
            <INFORMADOS>1</INFORMADOS>
            <ACEPTADOS>0</ACEPTADOS>
            <RECHAZADOS>0</RECHAZADOS>
            <REPAROS>1</REPAROS>
        </SII:RESP_BODY>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'objected')

    def test_analyze_sii_result_srv_code(self):
        sii_message = """<SII:RESPUESTA xmlns:SII="http://www.sii.cl/XMLSchema">
        <SII:RESP_HDR>
            <ESTADO>-11</ESTADO>
            <ERR_CODE>1</ERR_CODE>
            <SQL_CODE/>
            <SRV_CODE/>
            <NUM_ATENCION>532 ( 2004/06/14 16:44:20)</NUM_ATENCION>
        </SII:RESP_HDR>
        </SII:RESPUESTA>"""

        response_parsed = etree.fromstring(sii_message)
        self.assertEqual(self.env['l10n_cl.edi.util']._analyze_sii_result(response_parsed), 'ask_for_status')

    @patch('odoo.fields.Date.context_today', return_value=fields.Date.from_string('2019-11-23'))
    def test_create_invoice_from_attachment_with_accountant_user(self, context_today):
        partner_sii_same_company = self.env['res.partner'].create({
            'name': 'Other Partner SII Same Company',
            'is_company': 1,
            'company_id': self.company_data['company'].id,
            'vat': '76086428-1',
        })
        self.simple_accountman.email = 'test@test.test'

        att_name = 'incoming_invoice_33.xml'
        att_content = misc.file_open(f'l10n_cl_edi/tests/fetchmail_dtes/{att_name}', filter_ext=('.xml',)).read()
        attachment = self.env['ir.attachment'].with_user(self.simple_accountman).create({
            'name': att_name,
            'raw': att_content,
        })

        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail', return_value=None):
            moves = self.company_data['default_journal_sale'].with_user(self.simple_accountman)._create_document_from_attachment(attachment.ids)

        self.assertEqual(len(moves), 1)
        move = moves[0]
        self.assertEqual(move.name, 'FAC 000001')
        self.assertEqual(move.partner_id, partner_sii_same_company)
        self.assertEqual(move.date, fields.Date.from_string('2019-11-23'))
        self.assertEqual(move.invoice_date, fields.Date.from_string('2019-10-23'))
        self.assertEqual(move.invoice_date_due, fields.Date.from_string('2019-10-23'))
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_number, '000001')
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(move.company_id, self.company_data['company'])
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(move.currency_id.name, 'CLP')
