import base64
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestConsultarEstadoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.env.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Demo SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_download_code': 'DC',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id,
            'l10n_cr_fe_clave': '5' * 50, 'l10n_cr_fe_state': 'enviado',
        })

    def test_consultar_estado_aceptado_updates_state(self):
        xml = '<MensajeHacienda><DetalleMensaje>Comprobante aceptado</DetalleMensaje></MensajeHacienda>'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'aceptado', 'respuesta_xml': base64.b64encode(xml.encode()).decode()}):
            self.invoice.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'aceptado')
        self.assertIn('aceptado', self.invoice.l10n_cr_fe_respuesta_xml)

    def test_consultar_estado_rechazado_sets_motivo(self):
        xml = '<MensajeHacienda><DetalleMensaje>Cedula receptor invalida</DetalleMensaje></MensajeHacienda>'
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'rechazado', 'respuesta_xml': base64.b64encode(xml.encode()).decode()}):
            self.invoice.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'rechazado')
        self.assertEqual(self.invoice.l10n_cr_fe_motivo_rechazo, 'Cedula receptor invalida')

    def test_consultar_estado_pendiente_leaves_state_unchanged(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'procesando', 'respuesta_xml': None}):
            self.invoice.action_l10n_cr_fe_consultar_estado()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'enviado')
