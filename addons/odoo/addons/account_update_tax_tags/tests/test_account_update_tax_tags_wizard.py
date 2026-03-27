import time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged, freeze_time
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@freeze_time('2023-12-31')
@tagged('post_install', '-at_install')
class TestAccountUpdateTaxTagsWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        be_country_id = cls.env.ref('base.be').id
        cls.partner_agrolait = cls.env['res.partner'].create({
            'name': 'Deco Agrolait',
            'is_company': True,
            'country_id': cls.env.ref('base.us').id,
        })
        cls.company = cls.company_data['company']
        cls.company.write({'country_id': be_country_id})
        cls.tag_names = {
            'invoice_base': 'invoice_base_tag',
            'invoice_tax': 'invoice_tax_tag',
            'refund_base': 'refund_base_tag',
            'refund_tax': 'refund_tax_tag',
        }
        cls.tax_1 = cls._create_tax('update_test_tax', 15, tag_names=cls.tag_names)
        cls.wizard = cls.env['account.update.tax.tags.wizard'].create({'date_from': '2023-02-01'})

    def _create_invoice(self, move_type='out_invoice', invoice_amount=50, currency_id=None, partner_id=None, date_invoice=None, payment_term_id=False, auto_validate=False, taxes=None, state=None):
        if move_type == 'entry':
            raise AssertionError("Unexpected move_type : 'entry'.")

        if not taxes:
            taxes = self.env['account.tax']

        date_invoice = date_invoice or time.strftime('%Y') + '-07-01'

        invoice_vals = {
            'move_type': move_type,
            'partner_id': partner_id or self.partner_agrolait.id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'invoice_line_ids': [Command.create({
                'name': 'product that cost %s' % invoice_amount,
                'quantity': 1,
                'price_unit': invoice_amount,
                'tax_ids': [Command.set(taxes.ids)],
            })]
        }

        if payment_term_id:
            invoice_vals['invoice_payment_term_id'] = payment_term_id

        if currency_id:
            invoice_vals['currency_id'] = currency_id

        invoice = self.env['account.move'].with_context(default_move_type=move_type).create(invoice_vals)

        if state == 'cancel':
            invoice.write({'state': 'cancel'})
        elif auto_validate or state == 'posted':
            invoice.action_post()
        return invoice

    def create_invoice(self, move_type='out_invoice', invoice_amount=50, currency_id=None):
        return self._create_invoice(move_type=move_type, invoice_amount=invoice_amount, currency_id=currency_id, auto_validate=True)

    @classmethod
    def _create_or_get_tax_tag(cls, name, country_id=None):
        country_id = country_id or cls.company_data['company'].country_id.id
        tag = cls.env['account.account.tag'].search([
            ('name', '=', name),
            ('applicability', '=', 'taxes'),
            ('country_id', '=', country_id),
        ])
        if tag:
            return tag
        return cls.env['account.account.tag'].create({
            'name': name,
            'applicability': 'taxes',
            'country_id': country_id,
        })

    @classmethod
    def _create_tax(cls, name, amount, amount_type='percent', type_tax_use='sale', tag_names=None, children_taxes=None, tax_exigibility='on_invoice', **kwargs):
        if not tag_names:
            tag_names = {}
        tag_commands = {
            type_rep_line: [(Command.set(cls._create_or_get_tax_tag(tags).ids))]
            for type_rep_line, tags in tag_names.items()
        }
        vals = {
            'name': name,
            'amount': amount,
            'amount_type': amount_type,
            'type_tax_use': type_tax_use,
            'tax_exigibility': tax_exigibility,
            'children_tax_ids': [Command.set(children_taxes.ids)] if children_taxes else None,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': tag_commands.get('invoice_base'),
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': tag_commands.get('invoice_tax'),
                }),
            ] if not children_taxes else [],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': tag_commands.get('refund_base'),
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': tag_commands.get('refund_tax'),
                }),
            ] if not children_taxes else [],
            **kwargs,
        }
        return cls.env['account.tax'].create(vals)

    @classmethod
    def _change_tax_tag(cls, tax, new_tag, invoice=True, base=True):
        rep_lines = tax.invoice_repartition_line_ids if invoice else tax.refund_repartition_line_ids
        filtered_rep_lines = rep_lines.filtered(lambda rep_line: rep_line.repartition_type == ('base' if base else 'tax'))
        filtered_rep_lines.write({'tag_ids': [Command.set(cls._create_or_get_tax_tag(new_tag).ids)]})

    def _get_amls_by_type(self, moves):
        invoice_lines = moves.invoice_line_ids
        tax_lines = moves.line_ids.filtered('tax_line_id')
        counterpart_lines = moves.line_ids - invoice_lines - tax_lines
        return invoice_lines, tax_lines, counterpart_lines

    def test_update_tax_tags(self):
        """ When we change the tags on the taxes and use the wizard to update history,
        tags should be updated on amls within the wizard date range.
        """
        moves = self._create_invoice(taxes=self.tax_1) + self._create_invoice(taxes=self.tax_1)
        self._change_tax_tag(self.tax_1, 'invoice_tax_tag_changed', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        invoice_lines, tax_lines, counterpart_lines = self._get_amls_by_type(moves)
        self.assertEqual(invoice_lines.tax_tag_ids.name, 'invoice_base_tag', 'Base lines tags should not have changed.')
        self.assertEqual(tax_lines.tax_tag_ids.name, 'invoice_tax_tag_changed', 'Tax lines tags should have changed.')
        self.assertFalse(counterpart_lines.tax_tag_ids, 'Counterpart lines should not have changed.')

    def test_update_date_from(self):
        """ Only the amls that are concerned by the date_from constraint should be updated. """
        move_included = self._create_invoice(date_invoice='2023-02-23', taxes=self.tax_1)
        move_not_included = self._create_invoice(date_invoice='2023-01-23', taxes=self.tax_1)
        self._change_tax_tag(self.tax_1, 'invoice_tax_tag_changed', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        tax_line_included = move_included.line_ids.filtered(lambda aml: aml.tax_line_id)
        self.assertEqual(tax_line_included.tax_tag_ids.name, 'invoice_tax_tag_changed', 'Move within the date constraint should be updated.')
        tax_line_not_included = move_not_included.line_ids.filtered(lambda aml: aml.tax_line_id)
        self.assertEqual(tax_line_not_included.tax_tag_ids.name, 'invoice_tax_tag', 'Move outside the date constraint should not be updated.')

    def test_update_multiple_taxes(self):
        """ Test in case there are multiple taxes set on the invoice line. """
        tax_2 = self._create_tax('update_test_tax_2', 15, tag_names={
            'invoice_base': 'invoice_base_tag_2',
            'invoice_tax': 'invoice_tax_tag_2',
            'refund_base': 'refund_base_tag_2',
            'refund_tax': 'refund_tax_tag_2',
        })
        move = self._create_invoice(taxes=self.tax_1 + tax_2)
        self._change_tax_tag(self.tax_1, 'invoice_tax_tag_changed', invoice=True, base=False)
        self._change_tax_tag(tax_2, 'invoice_tax_tag_changed_2', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        invoice_line, tax_line, counterpart_line = self._get_amls_by_type(move)
        self.assertEqual(
            invoice_line.tax_tag_ids.sorted('name').mapped('name'),
            ['invoice_base_tag', 'invoice_base_tag_2'],
            'Base lines tags should not have changed.'
        )
        self.assertEqual(
            tax_line.tax_tag_ids.sorted('name').mapped('name'),
            ['invoice_tax_tag_changed', 'invoice_tax_tag_changed_2'],
            'Tax lines tags should have changed.'
        )
        self.assertFalse(counterpart_line.tax_tag_ids, 'Counterpart lines tags should not have changed.')

    def test_update_multi_company(self):
        """ Tests that only the company that is selected when opening the wizard will have its amls updated. """
        move_1 = self._create_invoice(taxes=self.tax_1)
        self._change_tax_tag(self.tax_1, 'invoice_tax_tag_changed_for_company_1', invoice=True, base=False)
        be_country_id = self.env.ref('base.be').id

        company_2 = self.setup_other_company()['company']
        company_2.write({'country_id': be_country_id})
        self.env.user.company_id = company_2
        tax_2 = self._create_tax(
            'update_test_tax_2',
            15,
            tag_names={'invoice_tax': 'update_test_invoice_tax_tag_company_2'}
        )
        move_2 = self._create_invoice(taxes=tax_2)
        self._change_tax_tag(tax_2, 'invoice_tax_tag_changed_for_company_2', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        tax_line_1 = move_1.line_ids.filtered(lambda aml: aml.tax_line_id)
        tax_line_2 = move_2.line_ids.filtered(lambda aml: aml.tax_line_id)
        # Only the first move_id should be updated since it belongs to first company which was initialized in the wizard
        self.assertEqual(tax_line_1.tax_tag_ids.name, 'invoice_tax_tag_changed_for_company_1')
        self.assertEqual(tax_line_2.tax_tag_ids.name, 'update_test_invoice_tax_tag_company_2')

    def test_update_all_move_type(self):
        """ Tests that all move type are correctly updated with the corresponding tags. """
        move_types = [
            # 'entry' tested in test_update_move_type_entry since it's more complex
            'out_invoice',
            'in_invoice',
            'out_refund',
            'in_refund',
            'in_receipt',
            'out_receipt',
        ]
        for move_type in move_types:
            for line_type in ['base', 'tax']:
                with self.subTest(f'Update tax tag on {move_type}-{line_type}'):
                    type_tax_use = 'sale' if move_type.startswith('out_') else 'purchase'
                    tax_2 = self._create_tax(f'update_test_tax_2_{move_type}_{line_type}', 15, type_tax_use=type_tax_use, tag_names={
                        'invoice_base': 'test_tag_invoice_base',
                        'invoice_tax': 'test_tag_invoice_tax',
                        'refund_base': 'test_tag_refund_base',
                        'refund_tax': 'test_tag_refund_tax',
                    })
                    move = self._create_invoice(move_type=move_type, taxes=tax_2)
                    super_type = move_type.split('_')[1]
                    if super_type == 'receipt':
                        super_type = 'invoice'  # receipt type acts just like invoice one
                    self._change_tax_tag(tax_2, f'{move_type}_{line_type}_tag_changed', invoice=super_type == 'invoice', base=line_type == 'base')
                    self.wizard.update_amls_tax_tags()

                    invoice_line, tax_line, counterpart_line = self._get_amls_by_type(move)
                    if line_type == 'base':
                        self.assertEqual(invoice_line.tax_tag_ids.name, f'{move_type}_{line_type}_tag_changed', 'Base lines tags should have changed.')
                        self.assertEqual(tax_line.tax_tag_ids.name, f'test_tag_{super_type}_tax', 'Tax lines tags should not have changed.')
                        self.assertFalse(counterpart_line.tax_tag_ids, 'Counterpart lines tags should not have changed.')
                    else:
                        self.assertEqual(invoice_line.tax_tag_ids.name, f'test_tag_{super_type}_base', 'Base lines tags should not have changed.')
                        self.assertEqual(tax_line.tax_tag_ids.name, f'{move_type}_{line_type}_tag_changed', 'Tax lines tags should have changed.')
                        self.assertFalse(counterpart_line.tax_tag_ids, 'Counterpart lines tags should not have changed.')

    def test_update_move_type_entry(self):
        """ Test that move of type 'entry' are correctly updated.
        If a line has a negative balance and use a sale tax, it should act as an invoice.
        If a line has a positive balance and use a sale tax, it should act as a refund.
        If a line has a negative balance and use a purchase tax, it should act as a refund.
        If a line has a positive balance and use a purchase tax, it should be treated as an invoice.
        """
        account = self.company_data['default_account_assets']  # Account is not relevant for the test but must be set.
        for tax_type in ['sale', 'purchase']:
            tax = self._create_tax(f'test_{tax_type}_tax', 10, type_tax_use=tax_type, tag_names=self.tag_names)
            for balance in [-1000, 1000]:
                with self.subTest(f'Testing move type entry {tax_type}: {balance}'):
                    move = self.env['account.move'].create({
                        'move_type': 'entry',
                        'line_ids': [
                            Command.create({
                                "name": "line name",
                                "account_id": account.id,
                                'tax_ids': [Command.set(tax.ids)],
                                "balance": balance,
                            }),
                        ]
                    })

                    self._change_tax_tag(tax, 'invoice_base_tag_changed', invoice=True, base=True)
                    self._change_tax_tag(tax, 'refund_base_tag_changed', invoice=False, base=True)

                    self.wizard.update_amls_tax_tags()
                    invoice_line, tax_line, _ = self._get_amls_by_type(move)
                    if (balance < 0 and tax_type == 'sale') or (balance > 0 and tax_type == 'purchase'):
                        self.assertEqual(invoice_line.tax_tag_ids.name, 'invoice_base_tag_changed')
                        self.assertEqual(tax_line.tax_tag_ids.name, 'invoice_tax_tag')
                    elif (balance < 0 and tax_type == 'purchase') or (balance > 0 and tax_type == 'sale'):
                        self.assertEqual(invoice_line.tax_tag_ids.name, 'refund_base_tag_changed')
                        self.assertEqual(tax_line.tax_tag_ids.name, 'refund_tax_tag')

    def test_update_amls_all_states(self):
        """ Tests that moves are correctly updated, regardless of their state. """
        move_states = ('posted', 'cancel', 'draft')
        moves = [self._create_invoice(partner_id=self.partner_a.id, taxes=self.tax_1, state=state) for state in move_states]
        self._change_tax_tag(self.tax_1, 'invoice_base_tag_changed', invoice=True, base=True)
        self._change_tax_tag(self.tax_1, 'invoice_tax_tag_changed', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()
        for move in moves:
            with self.subTest(f'Update tax tag on move with state: {move.state}'):
                invoice_line, tax_line, counterpart_line = self._get_amls_by_type(move)
                self.assertEqual(invoice_line.tax_tag_ids.name, 'invoice_base_tag_changed', 'Base lines tags should have changed.')
                self.assertEqual(tax_line.tax_tag_ids.name, 'invoice_tax_tag_changed', 'Tax lines tags should have changed.')
                self.assertFalse(counterpart_line.tax_tag_ids, 'Counterpart lines tags should not have changed.')

    def test_update_no_tag_before(self):
        """ Tests that update happens on aml that had no tag previously. """
        tax = self._create_tax('test_tax_no_tag', 15)
        move = self._create_invoice(taxes=tax)
        self._change_tax_tag(tax, 'new_tag_name', invoice=True, base=True)
        self.wizard.update_amls_tax_tags()

        self.assertEqual(move.invoice_line_ids.tax_tag_ids.name, 'new_tag_name')

    def test_update_no_tag_after(self):
        move = self._create_invoice(taxes=self.tax_1)
        self.tax_1.invoice_repartition_line_ids.write({'tag_ids': [Command.clear()]})  # Command.CLEAR both base and tax lines
        self.wizard.update_amls_tax_tags()

        invoice_line, tax_line, counterpart_line = self._get_amls_by_type(move)
        self.assertFalse(invoice_line.tax_tag_ids, 'Base lines tags should be empty.')
        self.assertFalse(tax_line.tax_tag_ids, 'Tax lines should be empty.')
        self.assertFalse(counterpart_line.tax_tag_ids, 'Counterpart lines tags should not have changed.')

    def test_update_child_tax(self):
        """ Make sure groups of taxes are correctly handled. """
        tax_child_1 = self._create_tax('tax_child_1', 15, type_tax_use='purchase', tag_names={
            'invoice_base': 'invoice_base_tag_child_1',
            'invoice_tax': 'invoice_tax_tag_child_1',
            'refund_base': 'refund_base_tag_child_1',
            'refund_tax': 'refund_tax_tag_child_1',
        })
        tax_child_2 = self._create_tax('tax_child_2', 15, type_tax_use='none', tag_names={
            'invoice_base': 'invoice_base_tag_child_2',
            'invoice_tax': 'invoice_tax_tag_child_2',
            'refund_base': 'refund_base_tag_child_2',
            'refund_tax': 'refund_tax_tag_child_2',
        })
        tax_parent = self._create_tax('tax_parent', 15, amount_type='group', type_tax_use='purchase', children_taxes=(tax_child_1 + tax_child_2))
        move = self._create_invoice(taxes=tax_parent)

        # Check that lines are set as expected before update.
        invoice_line, tax_lines, counterpart_line = self._get_amls_by_type(move)
        self.assertEqual(invoice_line.tax_tag_ids.sorted('name').mapped('name'), ['invoice_base_tag_child_1', 'invoice_base_tag_child_2'])
        self.assertEqual(tax_lines.tax_tag_ids.sorted('name').mapped('name'), ['invoice_tax_tag_child_1', 'invoice_tax_tag_child_2'])
        self.assertFalse(counterpart_line.tax_tag_ids)

        self._change_tax_tag(tax_child_1, 'invoice_base_tag_1_changed', invoice=True, base=True)
        self._change_tax_tag(tax_child_1, 'invoice_tax_tag_1_changed', invoice=True, base=False)
        self._change_tax_tag(tax_child_2, 'invoice_base_tag_2_changed', invoice=True, base=True)
        self._change_tax_tag(tax_child_2, 'invoice_tax_tag_2_changed', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        invoice_line, tax_lines, counterpart_line = self._get_amls_by_type(move)
        self.assertEqual(invoice_line.tax_tag_ids.sorted('name').mapped('name'), ['invoice_base_tag_1_changed', 'invoice_base_tag_2_changed'])
        self.assertEqual(tax_lines.tax_tag_ids.sorted('name').mapped('name'), ['invoice_tax_tag_1_changed', 'invoice_tax_tag_2_changed'])
        self.assertFalse(counterpart_line.tax_tag_ids)

    def test_update_with_caba_taxes(self):
        """  Ensure the CABA (cash basis) moves linked to the invoices are updated too. """
        self.env.company.tax_exigibility = True
        tax = self._create_tax('caba_tax', 15, tag_names=self.tag_names, tax_exigibility='on_payment')
        invoice = self._create_invoice(taxes=tax, state='posted')
        # make payment
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()
        partial_rec = invoice.line_ids.matched_credit_ids
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])

        self._change_tax_tag(tax, 'invoice_base_tag_changed', invoice=True, base=True)
        self._change_tax_tag(tax, 'invoice_tax_tag_changed', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        invoice_lines, tax_lines, counterpart_lines = self._get_amls_by_type(invoice)
        self.assertEqual(invoice_lines.tax_tag_ids.name, 'invoice_base_tag_changed', 'Base lines tags should have changed.')
        self.assertEqual(tax_lines.tax_tag_ids.name, 'invoice_tax_tag_changed', 'Tax lines tags should have changed.')
        self.assertFalse(counterpart_lines.tax_tag_ids, 'Counterpart lines should not have changed.')

        caba_base_line = caba_move.line_ids.filtered('tax_ids')
        caba_tax_line = caba_move.line_ids.filtered('tax_line_id')
        caba_counterpart_lines = caba_move.line_ids - caba_base_line - caba_tax_line
        self.assertEqual(caba_base_line.tax_tag_ids.name, 'invoice_base_tag_changed', 'CABA base lines tags should have changed.')
        self.assertEqual(caba_tax_line.tax_tag_ids.name, 'invoice_tax_tag_changed', 'CABA tax lines tags should have changed.')
        self.assertFalse(caba_counterpart_lines.tax_tag_ids, 'CABA counterpart lines should not have changed.')

    def test_update_caba_taxes_with_negative_line(self):
        self.company.tax_exigibility = True
        tax = self._create_tax('caba_tax', 15, tag_names=self.tag_names, tax_exigibility='on_payment')
        invoice = self.init_invoice('out_invoice', invoice_date='2023-02-23', amounts=[-50, 100], taxes=tax, post=True)
        # make payment
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()
        partial_rec = invoice.line_ids.matched_credit_ids

        self._change_tax_tag(tax, 'invoice_base_tag_changed', invoice=True, base=True)
        self._change_tax_tag(tax, 'invoice_tax_tag_changed', invoice=True, base=False)
        self.wizard.update_amls_tax_tags()

        invoice_lines, tax_lines, counterpart_lines = self._get_amls_by_type(invoice)
        self.assertEqual(invoice_lines.tax_tag_ids.name, 'invoice_base_tag_changed', 'Base lines tags should have changed.')
        self.assertEqual(tax_lines.tax_tag_ids.name, 'invoice_tax_tag_changed', 'Tax lines tags should have changed.')
        self.assertFalse(counterpart_lines.tax_tag_ids, 'Counterpart lines should not have changed.')

        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        caba_base_line = caba_move.line_ids.filtered('tax_ids')
        caba_tax_line = caba_move.line_ids.filtered('tax_line_id')
        caba_counterpart_lines = caba_move.line_ids - caba_base_line - caba_tax_line
        self.assertEqual(caba_base_line.tax_tag_ids.name, 'invoice_base_tag_changed', 'CABA base lines tags should have changed.')
        self.assertEqual(caba_tax_line.tax_tag_ids.name, 'invoice_tax_tag_changed', 'CABA tax lines tags should have changed.')
        self.assertFalse(caba_counterpart_lines.tax_tag_ids, 'CABA counterpart lines should not have changed.')

    def test_child_tax_multiple_parent_raises(self):
        tax_child = self._create_tax('tax_child_1', 15)
        tax_parent_1 = self._create_tax('tax_parent', 15, amount_type='group', children_taxes=tax_child)
        self._create_tax('tax_parent_2', 15, amount_type='group', children_taxes=tax_child)
        self._create_invoice(taxes=tax_parent_1)
        with self.assertRaisesRegex(UserError, 'Update with children taxes that are child of multiple parents is not supported.'):
            self.wizard.update_amls_tax_tags()
