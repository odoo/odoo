from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestReintentarFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas Demo Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
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
            'certificate_pin': '1234',
            'certificate_download_code': 'DC',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'company_id': self.company.id, 'partner_id': partner.id,
            'l10n_cr_fe_clave': '1' * 50, 'l10n_cr_fe_state': 'rechazado',
            'l10n_cr_fe_motivo_rechazo': 'Cedula receptor invalida',
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def test_reintentar_generates_new_clave_and_succeeds(self):
        nueva_clave = '9' * 50
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   return_value={'clave': nueva_clave, 'consecutivo': '0' * 20}), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_fe',
                   return_value='<FacturaElectronica/>'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                   return_value='<FacturaElectronica firmada="1"/>'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                   return_value={'http_status': 202, 'raw': []}):
            self.invoice.action_l10n_cr_fe_reintentar()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'enviado')
        self.assertEqual(self.invoice.l10n_cr_fe_clave, nueva_clave)
        self.assertNotEqual(self.invoice.l10n_cr_fe_clave, '1' * 50)
        self.assertFalse(self.invoice.l10n_cr_fe_motivo_rechazo)
