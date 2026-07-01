from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveMapping(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Demo',
            'vat': '102340567',
        })
        product = self.env['product.product'].create({'name': 'Producto demo'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'name': 'Producto demo',
            })],
        })

    def test_build_detalles_has_required_fields(self):
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        self.assertEqual(len(detalles), 1)
        d = detalles[0]
        for field in ('codigoCABYS', 'subTotal', 'impuestoAsumidoEmisorFabrica',
                      'impuestoNeto', 'cantidad', 'unidadMedida', 'detalle',
                      'precioUnitario', 'montoTotal', 'montoTotalLinea'):
            self.assertIn(field, d)
        self.assertEqual(d['cantidad'], 1.0)
        self.assertEqual(d['precioUnitario'], 1000.0)

    def test_build_clave_params(self):
        params = self.invoice._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'FE')
        self.assertEqual(params['situacion'], 'normal')
        self.assertEqual(params['cedula'], '702320717')
        self.assertEqual(len(params['codigoSeguridad']), 8)
        self.assertTrue(params['codigoSeguridad'].isdigit())

    def test_build_genxml_params_serializes_detalles(self):
        import json
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        params = self.invoice._l10n_cr_fe_build_genxml_params('5' * 50, '0' * 20, detalles)
        self.assertEqual(params['clave'], '5' * 50)
        self.assertEqual(params['consecutivo'], '0' * 20)
        self.assertEqual(params['receptor_num_identif'], '102340567')
        # detalles y medios_pago van serializados como JSON string
        self.assertIsInstance(params['detalles'], str)
        self.assertEqual(json.loads(params['detalles'])[0]['codigoCABYS'], '0111101000000')
        self.assertIsInstance(params['medios_pago'], str)
