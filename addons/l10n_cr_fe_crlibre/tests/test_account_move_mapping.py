from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveMapping(TransactionCase):

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
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Demo',
            'vat': '102340567',
        })
        self.product = self.env['product.product'].create({
            'name': 'Producto demo',
        })
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_build_clave_params(self):
        params = self.invoice._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'FE')
        self.assertEqual(params['situacion'], 'normal')
        self.assertEqual(params['cedula'], '702320717')
        self.assertEqual(len(params['codigoSeguridad']), 8)
        self.assertTrue(params['codigoSeguridad'].isdigit())

    def test_build_genxml_params_uses_company_config(self):
        import json
        detalles = [{'codigoCABYS': '0111101000000', 'cantidad': 1, 'unidadMedida': 'Unid',
                     'detalle': 'x', 'precioUnitario': 1000.0, 'montoTotal': 1000.0,
                     'subTotal': 1000.0, 'baseImponible': 1000.0,
                     'impuestoAsumidoEmisorFabrica': 0, 'impuestoNeto': 0.0,
                     'montoTotalLinea': 1000.0}]
        params = self.invoice._l10n_cr_fe_build_genxml_params('5' * 50, '0' * 20, detalles)
        self.assertEqual(params['emisor_nombre'], 'Frutas Demo SA')
        self.assertEqual(params['emisor_num_identif'], '702320717')
        self.assertEqual(params['receptor_num_identif'], '102340567')
        self.assertIsInstance(params['detalles'], str)
        self.assertEqual(json.loads(params['detalles'])[0]['codigoCABYS'], '0111101000000')
