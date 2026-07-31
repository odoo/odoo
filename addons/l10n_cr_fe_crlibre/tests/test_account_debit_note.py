from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountDebitNoteFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas Debit Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Debit Test SA',
            'economic_activity_code': '011101',
            'province': '1', 'canton': '01', 'district': '08', 'neighborhood': '01',
            'address_detail': 'Local de demostración',
            'email': 'demo@frutasdemo.cr',
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'vat': '102340567'})
        self.product = self.env['product.product'].create({
            'name': 'Producto demo', 'l10n_cr_fe_cabys': '0111101000000'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'quantity': 1, 'price_unit': 1000.0,
                'name': 'Producto demo', 'tax_ids': [(6, 0, [])],
            })],
        })
        self.invoice.action_post()

    def test_motivo_nd_computes_expected_codigo_referencia(self):
        wizard = self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'l10n_cr_fe_motivo_nd': 'cargo_financiero',
            })
        self.assertEqual(wizard.l10n_cr_fe_codigo_referencia, '10')

    def test_applicable_true_for_accepted_fe_invoice(self):
        wizard = self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({})
        self.assertTrue(wizard.l10n_cr_fe_applicable)

    def test_create_debit_copies_motivo_to_debit_note(self):
        wizard = self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'l10n_cr_fe_motivo_nd': 'correccion_monto',
                'reason': 'Se facturó de menos por error de digitación',
            })
        action = wizard.create_debit()
        debit_note = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(debit_note.l10n_cr_fe_motivo_nd, 'correccion_monto')
        self.assertEqual(debit_note.l10n_cr_fe_codigo_referencia, '02')
        self.assertEqual(debit_note.l10n_cr_fe_razon, 'Se facturó de menos por error de digitación')
        self.assertEqual(debit_note.debit_origin_id, self.invoice)
