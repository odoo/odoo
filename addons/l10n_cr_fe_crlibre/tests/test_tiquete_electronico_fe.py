from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTiqueteElectronicoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas TE Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas TE Test SA',
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

    def _create_tiquete(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_es_tiquete': True,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '8' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_te',
                  return_value='<TiqueteElectronico>sin firmar</TiqueteElectronico>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<TiqueteElectronico>firmada</TiqueteElectronico>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_sends_tiquete_using_gen_xml_te(self):
        tiquete = self._create_tiquete()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            tiquete.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(tiquete.l10n_cr_fe_state, 'enviado')
        self.assertEqual(tiquete.l10n_cr_fe_clave, '8' * 50)
        self.assertIn('firmada', tiquete.l10n_cr_fe_xml_firmado)
