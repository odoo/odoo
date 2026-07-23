from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestNotaCreditoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas NC Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas NC Test SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
            'certificate_download_code': 'DC_YA_SUBIDO',
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        self.product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.original_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_fecha_emision': '2026-07-01T10:00:00-06:00',
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _create_credit_note(self):
        return self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'reversed_entry_id': self.original_invoice.id,
            'l10n_cr_fe_motivo': 'devolucion_mercancia',
            'l10n_cr_fe_codigo_referencia': '06',
            'l10n_cr_fe_razon': 'Producto dañado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '9' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_nc',
                  return_value='<NotaCreditoElectronica>sin firmar</NotaCreditoElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<NotaCreditoElectronica>firmada</NotaCreditoElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_sends_credit_note_using_gen_xml_nc(self):
        credit_note = self._create_credit_note()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            credit_note.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(credit_note.l10n_cr_fe_state, 'enviado')
        self.assertEqual(credit_note.l10n_cr_fe_clave, '9' * 50)
        self.assertIn('firmada', credit_note.l10n_cr_fe_xml_firmado)

    def test_action_post_blocks_credit_note_when_original_not_aceptado(self):
        self.original_invoice.l10n_cr_fe_state = 'enviado'
        credit_note = self._create_credit_note()
        credit_note.action_post()
        self.assertEqual(credit_note.state, 'posted')
        self.assertEqual(credit_note.l10n_cr_fe_state, 'error')

    def test_consultar_estado_aceptado_sends_email_for_credit_note(self):
        import base64 as base64_module
        credit_note = self._create_credit_note()
        credit_note.write({'l10n_cr_fe_clave': '9' * 50, 'l10n_cr_fe_state': 'enviado'})
        self.partner.email = 'cliente@example.com'
        xml = '<MensajeHacienda><DetalleMensaje>Comprobante aceptado</DetalleMensaje></MensajeHacienda>'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'aceptado',
                                 'respuesta_xml': base64_module.b64encode(xml.encode()).decode()}), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.account_move.AccountMove._l10n_cr_fe_send_acceptance_email') as m_email:
            credit_note.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(credit_note.l10n_cr_fe_state, 'aceptado')
        m_email.assert_called_once()
