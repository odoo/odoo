from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveReversalFe(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas Reversal Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env['l10n_cr.fe.config'].create({
            'company_id': self.company.id,
            'environment': 'stag',
            'identification_type': '01',
            'identification_number': '702320717',
            'legal_name': 'Frutas Reversal Test SA',
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

    def test_motivo_computes_expected_codigo_referencia(self):
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'devolucion_mercancia',
            })
        self.assertEqual(wizard.l10n_cr_fe_codigo_referencia, '06')

    def test_applicable_true_for_accepted_fe_invoice(self):
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
            })
        self.assertTrue(wizard.l10n_cr_fe_applicable)

    def test_refund_moves_copies_motivo_to_credit_note(self):
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'correccion_monto',
                'reason': 'Ajuste de precio acordado con el cliente',
                'l10n_cr_fe_line_ids': [(6, 0, self.invoice.invoice_line_ids.ids)],
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(credit_note.l10n_cr_fe_motivo, 'correccion_monto')
        self.assertEqual(credit_note.l10n_cr_fe_codigo_referencia, '02')
        self.assertEqual(credit_note.l10n_cr_fe_razon, 'Ajuste de precio acordado con el cliente')
        self.assertEqual(credit_note.reversed_entry_id, self.invoice)

    def test_refund_moves_requires_at_least_one_selected_line_for_partial_motivo(self):
        from odoo.exceptions import UserError
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'correccion_monto',
            })
        with self.assertRaises(UserError):
            wizard.refund_moves()

    def test_refund_moves_anulacion_total_does_not_require_line_selection(self):
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'journal_id': self.invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'anulacion_total',
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 1)

    def _create_multi_line_invoice(self):
        product_b = self.env['product.product'].create({
            'name': 'Producto B', 'l10n_cr_fe_cabys': '0111101000001'})
        product_c = self.env['product.product'].create({
            'name': 'Producto C', 'l10n_cr_fe_cabys': '0111101000002'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'l10n_cr_fe_clave': '6' * 50,
            'l10n_cr_fe_state': 'aceptado',
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product.id, 'quantity': 5, 'price_unit': 1200.0,
                        'name': 'Producto demo', 'tax_ids': [(6, 0, [])]}),
                (0, 0, {'product_id': product_b.id, 'quantity': 1, 'price_unit': 600.0,
                        'name': 'Producto B', 'tax_ids': [(6, 0, [])]}),
                (0, 0, {'product_id': product_c.id, 'quantity': 5, 'price_unit': 1500.0,
                        'name': 'Producto C', 'tax_ids': [(6, 0, [])]}),
            ],
        })
        invoice.action_post()
        return invoice

    def test_refund_moves_keeps_only_selected_lines(self):
        invoice = self._create_multi_line_invoice()
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'correccion_monto',
                'l10n_cr_fe_line_ids': [(6, 0, lines[0].ids)],
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 1)
        self.assertEqual(credit_lines.product_id, lines[0].product_id)
        self.assertEqual(credit_lines.quantity, 5)

    def test_refund_moves_keeps_multiple_selected_lines(self):
        invoice = self._create_multi_line_invoice()
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        selected = lines[0] | lines[2]
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'devolucion_mercancia',
                'l10n_cr_fe_line_ids': [(6, 0, selected.ids)],
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 2)
        self.assertEqual(
            set(credit_lines.mapped('product_id.id')),
            {lines[0].product_id.id, lines[2].product_id.id})

    def test_refund_moves_anulacion_total_keeps_all_lines_regardless_of_selection(self):
        invoice = self._create_multi_line_invoice()
        wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': invoice.journal_id.id,
                'l10n_cr_fe_motivo': 'anulacion_total',
            })
        action = wizard.refund_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_lines = credit_note.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(len(credit_lines), 3)
