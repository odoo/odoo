from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client import CrlibreApiError


@tagged('post_install', '-at_install')
class TestActionPostFe(TransactionCase):

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
            'certificate_pin': '1234',
            'certificate_download_code': 'DC_YA_SUBIDO',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def _patch_full_success(self):
        clave = '5' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_fe',
                  return_value='<FacturaElectronica>sin firmar</FacturaElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<FacturaElectronica>firmada</FacturaElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_success_sets_state_enviado(self):
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            self.invoice.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'enviado')
        self.assertEqual(self.invoice.l10n_cr_fe_clave, '5' * 50)
        self.assertIn('firmada', self.invoice.l10n_cr_fe_xml_firmado)

    def test_action_post_does_not_block_when_fe_fails(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   side_effect=CrlibreApiError('boom')):
            self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'error')

    def test_action_post_does_not_block_when_certificate_missing(self):
        config = self.env['l10n_cr.fe.config'].search([('company_id', '=', self.env.company.id)], limit=1)
        config.write({'certificate_download_code': False, 'certificate_file': False})
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, 'posted')
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'error')

    def test_action_post_does_not_block_when_product_missing_cabys(self):
        partner = self.env['res.partner'].create({'name': 'Cliente Sin Cabys', 'vat': '102340567'})
        product = self.env['product.product'].create({
            'name': 'Producto sin cabys', 'l10n_cr_fe_cabys': False})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Producto sin cabys',
            })],
        })
        # get_clave se llama antes que _l10n_cr_fe_build_detalles en el flujo; se mockea
        # para que la ejecución realmente llegue a la validación de CABYS que se quiere probar.
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   return_value={'clave': '5' * 50, 'consecutivo': '0' * 20}):
            invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cr_fe_state, 'error')

    def test_action_post_ignores_vendor_bills(self):
        partner = self.env['res.partner'].create({'name': 'Proveedor Demo'})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.context_today(self.invoice),
            'invoice_line_ids': [(0, 0, {'quantity': 1, 'price_unit': 100.0, 'name': 'Gasto'})],
        })
        bill.action_post()
        self.assertEqual(bill.l10n_cr_fe_state, 'draft')
