from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveMapping(TransactionCase):

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
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Demo',
            'vat': '102340567',
        })
        self.product = self.env['product.product'].create({
            'name': 'Producto demo',
            'l10n_cr_fe_cabys': '0111101000000',
        })
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'name': 'Producto demo',
                'tax_ids': [(6, 0, [])],
            })],
        })

    def test_build_clave_params(self):
        params = self.invoice._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'FE')
        self.assertEqual(params['situacion'], 'normal')
        self.assertEqual(params['cedula'], '702320717')
        self.assertEqual(len(params['codigoSeguridad']), 8)
        self.assertTrue(params['codigoSeguridad'].isdigit())
        self.assertEqual(len(params['consecutivo']), 10)
        self.assertTrue(params['consecutivo'].isdigit())

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
        self.assertEqual(params['receptor_tipo_identif'], '01')
        self.assertIsInstance(params['detalles'], str)
        self.assertEqual(json.loads(params['detalles'])[0]['codigoCABYS'], '0111101000000')

    def test_build_genxml_params_without_receptor_vat_raises(self):
        from odoo.exceptions import UserError
        self.partner.vat = False
        with self.assertRaises(UserError):
            self.invoice._l10n_cr_fe_build_genxml_params('5' * 50, '0' * 20, [])

    def test_build_genxml_params_computes_resumen_totals(self):
        import json
        gravado = self._create_invoice_with_tax(13)
        detalles = gravado._l10n_cr_fe_build_detalles()
        params = gravado._l10n_cr_fe_build_genxml_params('5' * 50, '0' * 20, detalles)
        self.assertEqual(params['total_merc_gravada'], 1000.0)
        self.assertEqual(params['total_gravados'], 1000.0)
        self.assertEqual(params['total_exento'], 0)
        self.assertEqual(params['total_ventas'], 1000.0)
        self.assertEqual(params['total_impuestos'], 130.0)
        self.assertEqual(params['total_comprobante'], 1130.0)
        desglose = json.loads(params['totalDesgloseImpuesto'])
        self.assertEqual(len(desglose), 1)
        self.assertEqual(desglose[0]['CodigoTarifaIVA'], '08')
        self.assertEqual(desglose[0]['TotalMontoImpuesto'], 130.0)

    def test_build_detalles_uses_product_cabys(self):
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        self.assertEqual(len(detalles), 1)
        self.assertEqual(detalles[0]['codigoCABYS'], '0111101000000')
        for field in ('subTotal', 'impuestoAsumidoEmisorFabrica', 'impuestoNeto',
                      'cantidad', 'unidadMedida', 'detalle', 'precioUnitario',
                      'montoTotal', 'montoTotalLinea'):
            self.assertIn(field, detalles[0])

    def test_build_detalles_without_cabys_raises(self):
        from odoo.exceptions import UserError
        self.product.l10n_cr_fe_cabys = False
        with self.assertRaises(UserError):
            self.invoice._l10n_cr_fe_build_detalles()

    def _create_invoice_with_tax(self, tax_amount):
        tax = self.env['account.tax'].create({
            'name': 'IVA %s%%' % tax_amount,
            'amount_type': 'percent',
            'amount': tax_amount,
            'type_tax_use': 'sale',
            'company_id': self.company.id,
        })
        product = self.env['product.product'].create({
            'name': 'Producto con IVA %s%%' % tax_amount,
            'l10n_cr_fe_cabys': '0111101000000',
        })
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'name': product.name,
                'tax_ids': [(6, 0, [tax.id])],
            })],
        })

    def test_build_detalles_maps_1_percent_tax_to_codigo_tarifa_02(self):
        invoice = self._create_invoice_with_tax(1)
        detalle = invoice._l10n_cr_fe_build_detalles()[0]
        self.assertEqual(detalle['impuesto'][0]['codigoTarifa'], '02')
        self.assertEqual(detalle['impuesto'][0]['tarifa'], 1)

    def test_build_detalles_maps_13_percent_tax_to_codigo_tarifa_08(self):
        invoice = self._create_invoice_with_tax(13)
        detalle = invoice._l10n_cr_fe_build_detalles()[0]
        self.assertEqual(detalle['impuesto'][0]['codigoTarifa'], '08')
        self.assertEqual(detalle['impuesto'][0]['tarifa'], 13)

    def test_build_detalles_unsupported_tax_rate_raises(self):
        from odoo.exceptions import UserError
        invoice = self._create_invoice_with_tax(7)
        with self.assertRaises(UserError):
            invoice._l10n_cr_fe_build_detalles()

    def test_build_clave_params_nota_credito_uses_nc(self):
        original = self.invoice
        original.write({'l10n_cr_fe_clave': '5' * 50, 'l10n_cr_fe_state': 'aceptado'})
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'reversed_entry_id': original.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        params = credit_note._l10n_cr_fe_build_clave_params()
        self.assertEqual(params['tipoDocumento'], 'NC')
        self.assertEqual(len(params['consecutivo']), 10)

    def test_build_genxml_params_nota_credito_includes_informacion_referencia(self):
        import json as json_module
        original = self.invoice
        original.write({
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_fecha_emision': '2026-07-01T10:00:00-06:00',
            'l10n_cr_fe_state': 'aceptado',
        })
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'reversed_entry_id': original.id,
            'l10n_cr_fe_codigo_referencia': '06',
            'l10n_cr_fe_razon': 'Mercancía dañada en tránsito',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        detalles = credit_note._l10n_cr_fe_build_detalles()
        params = credit_note._l10n_cr_fe_build_genxml_params('9' * 50, '0' * 20, detalles)
        referencia = json_module.loads(params['informacion_referencia'])
        self.assertEqual(len(referencia), 1)
        self.assertEqual(referencia[0]['tipoDoc'], '01')
        self.assertEqual(referencia[0]['numero'], '5' * 50)
        self.assertEqual(referencia[0]['fechaEmision'], '2026-07-01T10:00:00-06:00')
        self.assertEqual(referencia[0]['codigo'], '06')
        self.assertEqual(referencia[0]['razon'], 'Mercancía dañada en tránsito')

    def test_build_genxml_params_factura_has_no_informacion_referencia(self):
        detalles = self.invoice._l10n_cr_fe_build_detalles()
        params = self.invoice._l10n_cr_fe_build_genxml_params('9' * 50, '0' * 20, detalles)
        self.assertNotIn('informacion_referencia', params)
