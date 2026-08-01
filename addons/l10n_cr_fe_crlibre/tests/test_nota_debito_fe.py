from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestNotaDebitoFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas ND Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas ND Test SA',
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
        self.original_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_fecha_emision': '2026-07-01T10:00:00-06:00',
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _create_debit_note(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'debit_origin_id': self.original_invoice.id,
            'l10n_cr_fe_motivo_nd': 'cargo_financiero',
            'l10n_cr_fe_codigo_referencia': '10',
            'l10n_cr_fe_razon': 'Interés por pago tardío',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 100.0,
                'name': 'Interés por mora', 'tax_ids': [(6, 0, [])],
            })],
        })

    def _patch_full_success(self):
        clave = '9' * 50
        return [
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave',
                  return_value={'clave': clave, 'consecutivo': '0' * 20}),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.gen_xml_nd',
                  return_value='<NotaDebitoElectronica>sin firmar</NotaDebitoElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_hacienda_token',
                  return_value='tok123'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.sign_xml',
                  return_value='<NotaDebitoElectronica>firmada</NotaDebitoElectronica>'),
            patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.send_fe',
                  return_value={'http_status': 202, 'raw': []}),
        ]

    def test_action_post_sends_debit_note_using_gen_xml_nd(self):
        debit_note = self._create_debit_note()
        patchers = self._patch_full_success()
        for p in patchers:
            p.start()
        try:
            debit_note.action_post()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(debit_note.l10n_cr_fe_state, 'enviado')
        self.assertEqual(debit_note.l10n_cr_fe_clave, '9' * 50)
        self.assertIn('firmada', debit_note.l10n_cr_fe_xml_firmado)

    def test_action_post_blocks_debit_note_when_original_not_aceptado(self):
        self.original_invoice.l10n_cr_fe_state = 'enviado'
        debit_note = self._create_debit_note()
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave') as m_get_clave:
            debit_note.action_post()
        self.assertEqual(debit_note.state, 'posted')
        self.assertEqual(debit_note.l10n_cr_fe_state, 'error')
        # Proves the block happened in our validation (before any client/network call), not
        # because of some unrelated failure (e.g. the sandbox's HTTP blocking) that happens to
        # also land in the same `except` and set the same error state.
        m_get_clave.assert_not_called()
        self.assertIn(
            'la factura original',
            ' '.join(debit_note.message_ids.mapped('body')),
        )

    def test_action_post_blocks_debit_note_when_original_is_nota_credito(self):
        nota_credito = self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '6' * 50,
            'l10n_cr_fe_fecha_emision': '2026-07-05T10:00:00-06:00',
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        debit_note = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'debit_origin_id': nota_credito.id,
            'l10n_cr_fe_motivo_nd': 'cargo_financiero',
            'l10n_cr_fe_codigo_referencia': '10',
            'l10n_cr_fe_razon': 'Interés por pago tardío',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 100.0,
                'name': 'Interés por mora', 'tax_ids': [(6, 0, [])],
            })],
        })
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave') as m_get_clave:
            debit_note.action_post()
        self.assertEqual(debit_note.state, 'posted')
        self.assertEqual(debit_note.l10n_cr_fe_state, 'error')
        # Proves the block happened in our validation (before any client/network call), not
        # because of some unrelated failure that happens to also land in the same `except`
        # and set the same error state.
        m_get_clave.assert_not_called()
        self.assertIn(
            'Cancelar una nota de crédito con una nota de débito no está soportado',
            ' '.join(debit_note.message_ids.mapped('body')),
        )

    def test_action_post_blocks_debit_note_on_tiquete_original(self):
        self.original_invoice.l10n_cr_fe_es_tiquete = True
        debit_note = self._create_debit_note()
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.CrlibreFeClient.get_clave') as m_get_clave:
            debit_note.action_post()
        self.assertEqual(debit_note.state, 'posted')
        self.assertEqual(debit_note.l10n_cr_fe_state, 'error')
        # Same rationale as above: pins down that this specific validation (Tiquete origin) fired,
        # not a generic/unrelated exception reaching the same `except (CrlibreApiError, UserError)`.
        m_get_clave.assert_not_called()
        self.assertIn(
            'Tiquete Electrónico',
            ' '.join(debit_note.message_ids.mapped('body')),
        )
