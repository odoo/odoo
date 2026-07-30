from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRecepcionProveedoresFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas MR Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas MR Test SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
            'hacienda_username': 'user@stag.comprobanteselectronicos.go.cr',
            'hacienda_password': 'secret',
            'certificate_pin': '1234',
            'certificate_download_code': 'DC_YA_SUBIDO',
        })
        self.partner = self.env['res.partner'].create({'name': 'Proveedor Demo', 'vat': '3101123456'})
        self.product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})

    def _create_bill(self):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.context_today(self.env.user),
            'l10n_cr_fe_proveedor_clave': '5' * 50,
            'l10n_cr_fe_proveedor_fecha_emision': '2026-07-27T10:00:00-06:00',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '7' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_mr',
                  return_value='<MensajeReceptor>sin firmar</MensajeReceptor>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<MensajeReceptor>firmada</MensajeReceptor>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_mr',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_aceptar_total_sends_cce_and_posts(self):
        bill = self._create_bill()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_aceptar_total()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'aceptado')
        self.assertEqual(bill.state, 'posted')
        self.assertEqual(bill.l10n_cr_fe_clave, '7' * 50)

    def test_aceptar_parcial_requires_motivo(self):
        bill = self._create_bill()
        with self.assertRaises(UserError):
            bill.action_l10n_cr_fe_aceptar_parcial()

    def test_aceptar_parcial_sends_cpce_and_posts(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_motivo = 'Cantidad recibida distinta a la facturada'
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_aceptar_parcial()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'aceptado_parcial')
        self.assertEqual(bill.state, 'posted')

    def test_rechazar_requires_motivo(self):
        bill = self._create_bill()
        with self.assertRaises(UserError):
            bill.action_l10n_cr_fe_rechazar()

    def test_rechazar_sends_rce_without_posting(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_motivo = 'Factura no corresponde a compra realizada'
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_rechazar()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'rechazado')
        self.assertEqual(bill.state, 'draft')

    def test_rechazar_then_manual_post_does_not_resend_mr(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_motivo = 'Factura no corresponde a compra realizada'
        patchers = self._patch_full_success()
        mocks = [p.start() for p in patchers]
        send_mr_mock = mocks[4]
        try:
            bill.action_l10n_cr_fe_rechazar()
            self.assertEqual(send_mr_mock.call_count, 1)
            self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
            self.assertEqual(bill.state, 'draft')

            # Native Odoo "Confirmar" is still available on the draft bill and
            # calls action_post(), which re-enters _l10n_cr_fe_generate_and_send().
            # It must not send a second Mensaje Receptor to Hacienda.
            bill.action_post()
            self.assertEqual(send_mr_mock.call_count, 1)
            self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        finally:
            for p in patchers:
                p.stop()

    def test_aceptar_total_twice_does_not_resend_cce(self):
        bill = self._create_bill()
        patchers = self._patch_full_success()
        mocks = [p.start() for p in patchers]
        send_mr_mock = mocks[4]
        try:
            bill.action_l10n_cr_fe_aceptar_total()
            self.assertEqual(send_mr_mock.call_count, 1)
            self.assertEqual(bill.state, 'posted')

            # Already sent and posted — re-invoking the dispatch method directly
            # (e.g. some other automation calling it again) must be a no-op.
            bill._l10n_cr_fe_generate_and_send()
            self.assertEqual(send_mr_mock.call_count, 1)
        finally:
            for p in patchers:
                p.stop()

    def test_rechazar_succeeds_when_product_has_no_cabys(self):
        product_sin_cabys = self.env['product.product'].create({'name': 'Producto sin CABYS'})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.context_today(self.env.user),
            'l10n_cr_fe_proveedor_clave': '5' * 50,
            'l10n_cr_fe_proveedor_fecha_emision': '2026-07-27T10:00:00-06:00',
            'l10n_cr_fe_mr_motivo': 'Factura no corresponde a compra realizada',
            'invoice_line_ids': [(0, 0, {
                'product_id': product_sin_cabys.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Producto sin CABYS', 'tax_ids': [(6, 0, [])],
            })],
        })
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_rechazar()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'rechazado')
        self.assertEqual(bill.state, 'draft')

    def test_aceptar_total_succeeds_when_product_has_no_cabys(self):
        product_sin_cabys = self.env['product.product'].create({'name': 'Producto sin CABYS'})
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.context_today(self.env.user),
            'l10n_cr_fe_proveedor_clave': '5' * 50,
            'l10n_cr_fe_proveedor_fecha_emision': '2026-07-27T10:00:00-06:00',
            'invoice_line_ids': [(0, 0, {
                'product_id': product_sin_cabys.id, 'quantity': 1, 'price_unit': 500.0,
                'name': 'Producto sin CABYS', 'tax_ids': [(6, 0, [])],
            })],
        })
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            bill.action_l10n_cr_fe_aceptar_total()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.state, 'posted')

    def test_aceptar_total_send_mr_envelope_uses_proveedor_clave_and_fecha(self):
        """El sobre enviado a Hacienda (send_mr) debe describir la factura original
        del proveedor (clave/fecha), no una clave/fecha inventada por nosotros, y el
        emisor/receptor del sobre debe coincidir con el proveedor/nuestra empresa
        (verificado contra un request real de la colección Postman de CRLibre)."""
        bill = self._create_bill()
        patchers = self._patch_full_success()
        mocks = [p.start() for p in patchers]
        send_mr_mock = mocks[4]
        try:
            bill.action_l10n_cr_fe_aceptar_total()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(send_mr_mock.call_count, 1)
        _, kwargs = send_mr_mock.call_args
        config = bill._l10n_cr_fe_get_config()
        self.assertEqual(kwargs['clave'], bill.l10n_cr_fe_proveedor_clave)
        self.assertEqual(kwargs['clave'], '5' * 50)
        self.assertEqual(kwargs['fecha_iso'], bill.l10n_cr_fe_proveedor_fecha_emision)
        self.assertEqual(kwargs['fecha_iso'], '2026-07-27T10:00:00-06:00')
        self.assertEqual(kwargs['emisor_num'], self.partner.vat)
        self.assertEqual(kwargs['receptor_num'], config.identification_number)
        # La clave/fecha propias del sobre nunca deben coincidir con la clave que
        # generamos nosotros (get_clave) para el consecutivo del Mensaje Receptor.
        self.assertNotEqual(kwargs['clave'], bill.l10n_cr_fe_clave)

    def test_action_post_bypass_without_motivo_raises_and_does_not_post(self):
        """Un usuario no debe poder saltarse la validación de motivo poniendo
        l10n_cr_fe_mr_decision directamente y usando el botón nativo "Confirmar"
        (action_post) en vez de action_l10n_cr_fe_rechazar/aceptar_parcial."""
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_decision = 'rechazado'
        with self.assertRaises(UserError):
            bill.action_post()
        self.assertEqual(bill.state, 'draft')
        self.assertNotEqual(bill.l10n_cr_fe_state, 'enviado')

    def test_consultar_estado_uses_proveedor_clave_for_in_invoice(self):
        """Verificado manualmente contra el sandbox real: Hacienda rastrea el
        Mensaje Receptor por la clave de la factura original del proveedor
        (la que se mandó en el sobre de sendMensaje), no por la clave propia
        que generamos para el consecutivo del Mensaje Receptor."""
        bill = self._create_bill()
        bill.write({'l10n_cr_fe_state': 'enviado', 'l10n_cr_fe_clave': '7' * 50})
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                   return_value='tok'), \
             patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.consultar_estado',
                   return_value={'ind_estado': 'desconocido', 'respuesta_xml': None}) as m_consultar:
            bill.action_l10n_cr_fe_consultar_estado()
        m_consultar.assert_called_once()
        clave_arg = m_consultar.call_args.args[1]
        self.assertEqual(clave_arg, bill.l10n_cr_fe_proveedor_clave)
        self.assertEqual(clave_arg, '5' * 50)
        self.assertNotEqual(clave_arg, bill.l10n_cr_fe_clave)

    def test_abrir_aceptar_parcial_bloquea_si_no_hay_cambios(self):
        """Si la factura quedó idéntica (en monto) al XML original del
        proveedor, no tiene sentido mandar una aceptación "parcial" — se debe
        forzar el uso de "Aceptar total" en su lugar."""
        bill = self._create_bill()
        bill.write({
            'l10n_cr_fe_proveedor_monto_impuesto': bill.amount_tax,
            'l10n_cr_fe_proveedor_total': bill.amount_total,
        })
        with self.assertRaises(UserError):
            bill.action_l10n_cr_fe_abrir_aceptar_parcial()

    def test_abrir_aceptar_parcial_permite_si_hay_cambios(self):
        bill = self._create_bill()
        bill.write({
            'l10n_cr_fe_proveedor_monto_impuesto': bill.amount_tax,
            'l10n_cr_fe_proveedor_total': bill.amount_total + 500,
        })
        action = bill.action_l10n_cr_fe_abrir_aceptar_parcial()
        self.assertEqual(action['res_model'], 'l10n_cr.fe.mr.motivo.wizard')
        self.assertEqual(action['context']['default_move_id'], bill.id)
        self.assertEqual(action['context']['default_decision'], 'aceptado_parcial')

    def test_abrir_aceptar_parcial_sin_proveedor_total_no_bloquea(self):
        """Facturas creadas antes del fix (o sin totales del proveedor
        capturados) no deben quedar bloqueadas — no hay base de comparación."""
        bill = self._create_bill()
        action = bill.action_l10n_cr_fe_abrir_aceptar_parcial()
        self.assertEqual(action['res_model'], 'l10n_cr.fe.mr.motivo.wizard')

    def test_aceptar_parcial_engine_bloquea_sin_cambios_aunque_se_llame_directo(self):
        """Protección contra bypass: aunque alguien llame directo al método
        que realmente envía (saltándose el botón/wizard), debe bloquearse
        igual si no hubo cambios reales."""
        bill = self._create_bill()
        bill.write({
            'l10n_cr_fe_mr_motivo': 'Motivo cualquiera',
            'l10n_cr_fe_proveedor_monto_impuesto': bill.amount_tax,
            'l10n_cr_fe_proveedor_total': bill.amount_total,
        })
        with self.assertRaises(UserError):
            bill.action_l10n_cr_fe_aceptar_parcial()
        self.assertNotEqual(bill.state, 'posted')

    def test_action_l10n_cr_fe_abrir_rechazar_returns_wizard_action(self):
        bill = self._create_bill()
        action = bill.action_l10n_cr_fe_abrir_rechazar()
        self.assertEqual(action['res_model'], 'l10n_cr.fe.mr.motivo.wizard')
        self.assertEqual(action['context']['default_move_id'], bill.id)
        self.assertEqual(action['context']['default_decision'], 'rechazado')

    def test_wizard_confirmar_aceptar_parcial(self):
        bill = self._create_bill()
        bill.write({
            'l10n_cr_fe_proveedor_monto_impuesto': bill.amount_tax,
            'l10n_cr_fe_proveedor_total': bill.amount_total + 500,
        })
        wizard = self.env['l10n_cr.fe.mr.motivo.wizard'].create({
            'move_id': bill.id,
            'decision': 'aceptado_parcial',
            'motivo': 'Cantidad recibida distinta a la facturada',
        })
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            result = wizard.action_confirmar()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})
        self.assertEqual(bill.l10n_cr_fe_mr_motivo, 'Cantidad recibida distinta a la facturada')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'aceptado_parcial')
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.state, 'posted')

    def test_wizard_confirmar_rechazar(self):
        bill = self._create_bill()
        wizard = self.env['l10n_cr.fe.mr.motivo.wizard'].create({
            'move_id': bill.id,
            'decision': 'rechazado',
            'motivo': 'Factura no corresponde a compra realizada',
        })
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            wizard.action_confirmar()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(bill.l10n_cr_fe_mr_motivo, 'Factura no corresponde a compra realizada')
        self.assertEqual(bill.l10n_cr_fe_mr_decision, 'rechazado')
        self.assertEqual(bill.l10n_cr_fe_state, 'enviado')
        self.assertEqual(bill.state, 'draft')

    def test_tipo_documento_resolves_per_decision(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_decision = 'aceptado'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'CCE')
        bill.l10n_cr_fe_mr_decision = 'aceptado_parcial'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'CPCE')
        bill.l10n_cr_fe_mr_decision = 'rechazado'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'RCE')
