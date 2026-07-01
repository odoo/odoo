from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client import CrlibreApiError


@tagged('post_install', '-at_install')
class TestGenerateAction(TransactionCase):

    def setUp(self):
        super().setUp()
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        product = self.env['product.product'].create({'name': 'Producto demo'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_generate_success(self):
        clave = '5' * 50
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   return_value={'clave': clave, 'consecutivo': '0' * 20}), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_fe',
                   return_value='<FacturaElectronica>ok</FacturaElectronica>'):
            self.invoice.action_l10n_cr_fe_generate()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'generated')
        self.assertEqual(self.invoice.l10n_cr_fe_clave, clave)
        self.assertIn('FacturaElectronica', self.invoice.l10n_cr_fe_xml)

    def test_generate_api_error_sets_state_error(self):
        # En error no se lanza excepción (no rompe la transacción): se persiste
        # el estado 'error' y se devuelve una notificación tipo 'danger'.
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                   side_effect=CrlibreApiError('boom')):
            result = self.invoice.action_l10n_cr_fe_generate()
        self.assertEqual(self.invoice.l10n_cr_fe_state, 'error')
        self.assertEqual(result['params']['type'], 'danger')
