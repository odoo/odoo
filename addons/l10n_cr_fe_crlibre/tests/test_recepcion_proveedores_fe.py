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

    def test_tipo_documento_resolves_per_decision(self):
        bill = self._create_bill()
        bill.l10n_cr_fe_mr_decision = 'aceptado'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'CCE')
        bill.l10n_cr_fe_mr_decision = 'aceptado_parcial'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'CPCE')
        bill.l10n_cr_fe_mr_decision = 'rechazado'
        self.assertEqual(bill._l10n_cr_fe_get_tipo_documento_info()['clave'], 'RCE')
