# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestThirdChecks(L10nLatamCheckTest):

    _test_user_groups = None  # FIXME list needed groups

    def create_third_party_check(self, journal=False, check_numbers=['00000001', '00000002']):
        if not journal:
            journal = self.third_party_check_journal
        vals = {
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': journal.id,
            'l10n_latam_new_check_ids': [
                Command.create({'name': check_numbers[0], 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
                Command.create({'name': check_numbers[1], 'payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 1}),
            ],
            'payment_method_line_id': journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'new_third_party_checks').id,
        }

        payment = self.env['account.payment'].create(vals)
        payment.action_post()
        return payment

    def _create_own_check(self):
        payment = self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal._get_available_payment_method_lines('outbound').filtered(
                lambda x: x.code == 'own_checks')[0].id,
            'l10n_latam_new_check_ids': [Command.create({
                'name': '00000003',
                'payment_date': fields.Date.add(fields.Date.today(), months=1),
                'amount': 1,
            })],
        })
        payment.action_post()
        return payment.l10n_latam_new_check_ids[0]

    def _create_branch_check_journal(self, company, code):
        parent_journal = self.third_party_check_journal
        return self.env['account.journal'].create({
            'name': 'Third Party Checks %s' % company.name,
            'code': code,
            'type': 'cash',
            'company_id': company.id,
            'outbound_payment_method_line_ids': [
                Command.create({
                    'payment_method_id': line.payment_method_id.id,
                    'payment_account_id': line.payment_account_id.id,
                }) for line in parent_journal.outbound_payment_method_line_ids
            ],
            'inbound_payment_method_line_ids': [
                Command.create({
                    'payment_method_id': line.payment_method_id.id,
                    'payment_account_id': line.payment_account_id.id,
                }) for line in parent_journal.inbound_payment_method_line_ids
            ],
        })

    def test_get_paid_with_multiple_checks(self):
        """ This a generic test to check that we are able to pay with checks
        We pay directly with multiple checks instead of just one check, just to ensure the create multi
        is properly working. """
        payment = self.create_third_party_check()
        checks = payment.l10n_latam_new_check_ids

        self.assertEqual(len(checks), 2, 'Checks where not created properly')
        self.assertRecordValues(checks, [{
            'current_journal_id': self.third_party_check_journal.id,
            'on_hand': True,
        }]*2)
        on_hand_checks = self.env['l10n_latam.check'].search([('on_hand', '=', True)])
        self.assertTrue(check in on_hand_checks for check in checks)  # ensure compute_sql is aligned

    # delivery (assert) dd un cheque tmb un return (assert) y un claim (assert)
    def test_third_party_check_delivery(self):
        payment = self.create_third_party_check()
        check = payment.l10n_latam_new_check_ids[0]
        # Check Delivery
        vals = {
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code in ('out_third_party_checks', 'return_third_party_checks')).id,
        }
        delivery = self.env['account.payment'].create(vals)
        delivery.action_post()
        self.assertFalse(check.current_journal_id, 'Current journal was not computed properly on delivery')
        self.assertFalse(check.on_hand, 'Check should not be on hand anymore once delivered')
        # check dont delivery twice
        with self.assertRaisesRegex(ValidationError, "it seems it has been moved by another payment"):
            self.env['account.payment'].create(vals).action_post()

        # Check Return / Rejection
        vals = {
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'amount': 1,
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'in_third_party_checks').id,
        }
        supplier_return = self.env['account.payment'].create(vals)
        supplier_return.action_post()
        self.assertEqual(check.current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on return')
        self.assertTrue(check.on_hand, 'Check should be on hand again once returned')
        # check dont return twice
        with self.assertRaisesRegex(ValidationError, "Some checks are already in hand and can't be received again"):
            self.env['account.payment'].create(vals).action_post()

        # Check Claim/Return to customer
        vals = {
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.rejected_check_journal.id,
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code in ('out_third_party_checks', 'return_third_party_checks')).id,
        }
        customer_return = self.env['account.payment'].create(vals)
        customer_return.action_post()
        self.assertFalse(check.current_journal_id, 'Current journal was not computed properly on customer return')
        # check dont claim twice
        with self.assertRaisesRegex(ValidationError, "Some checks are not anymore in journal,"):
            self.env['account.payment'].create(vals).action_post()

        operations = self.env['account.payment'].search([('l10n_latam_move_check_ids', '=', check.id), ('state', '!=', 'draft')], order="date desc, id desc")
        self.assertEqual(len(operations), 3, 'There should be 3 operations on the check')
        self.assertEqual(operations, customer_return | supplier_return | delivery)

    def test_deposit(self):
        payment = self.create_third_party_check()
        check = payment.l10n_latam_new_check_ids[0]
        bank_journal = self.company_data_3['default_journal_bank']

        # Deposit the check to the bank
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id]
        ).create({
            'to_journal_id': bank_journal.id,
        })._create_payments()
        self.assertEqual(check.current_journal_id.id, bank_journal.id, 'Current journal was not computed properly on delivery')
        self.assertFalse(check.on_hand, 'A check deposited on a bank journal is not on hand anymore')
        self.assertEqual(len(check.operation_ids + payment), 3, 'Check that all three payments were created')

        # If the bank tells you that the check has been rejected you have to do a new transfer of the previous check
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id]
        ).create({
            'to_journal_id': self.rejected_check_journal.id,
        })._create_payments()
        self.assertEqual(check.current_journal_id.id, self.rejected_check_journal.id, 'Current journal was not computed properly on delivery')
        self.assertTrue(check.on_hand, 'A check transferred back to a cash journal is on hand again')
        self.assertEqual(len(check.operation_ids + payment), 5, 'Check that all five payments were created')

        # Sent back to customer (with payment) - check if we can use the check
        self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.rejected_check_journal.id,
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'payment_method_line_id': self.rejected_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'new_third_party_checks').id,
        }).action_post()

    def test_check_transfer(self):
        """ Test transfer between third party checks journals """
        payment = self.create_third_party_check()
        check = payment.l10n_latam_new_check_ids[0]

        # Transfer to rejected checks journal (usually is to another third party checks journal, but for test purpose is the same)
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id]).create({'to_journal_id': self.rejected_check_journal.id})._create_payments()
        self.assertEqual(check.current_journal_id, self.rejected_check_journal, 'Current journal was not computed properly on delivery')

        # test that checks created on different journals but that are on same current journal, can be transfered together
        payment2 = self.create_third_party_check(journal=self.rejected_check_journal)
        check2 = payment2.l10n_latam_new_check_ids[0]
        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=[check.id, check2.id]).create({'to_journal_id': self.third_party_check_journal.id})._create_payments()

    def test_check_current_journal_with_both_operations(self):
        # -------------------------------
        # Case 1: inbound first, then outbound
        # -------------------------------
        inbound_payment = self.create_third_party_check()
        check = inbound_payment.l10n_latam_new_check_ids[0]

        # Check should be on hand after receiving
        self.assertEqual(
            check.current_journal_id,
            self.third_party_check_journal,
            "Check should be available after inbound operation"
        )

        # Create outbound payment and consume check
        outbound_payment = self.env['account.payment'].create({
            'l10n_latam_move_check_ids': [Command.set([check.id])],
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal
                ._get_available_payment_method_lines('outbound')
                .filtered(lambda x: x.code == 'out_third_party_checks').id,
        })
        outbound_payment.action_post()

        # Check should not be on hand after both operations
        self.assertFalse(
            check.current_journal_id,
            "Check with both inbound and outbound operations should not have current_journal_id set"
        )

        # -------------------------------
        # Case 2: outbound first, then inbound
        # -------------------------------
        first_now = datetime(2023, 11, 6, 8, 0, 0)
        second_now = first_now + timedelta(seconds=1)

        # Outbound creation with fixed now
        with self.mock_datetime_and_now(first_now):
            outbound_payment_2 = self.env['account.payment'].create({
                'partner_id': self.partner_a.id,
                'payment_type': 'outbound',
                'journal_id': self.third_party_check_journal.id,
                'payment_method_line_id': self.third_party_check_journal
                    ._get_available_payment_method_lines('outbound')
                    .filtered(lambda x: x.code == 'out_third_party_checks').id,
            })

        # Inbound creation with slightly later now
        with self.mock_datetime_and_now(second_now):
            inbound_payment_2 = self.create_third_party_check()
            check_2 = inbound_payment_2.l10n_latam_new_check_ids[0]

        # Link check to outbound
        outbound_payment_2.write({'l10n_latam_move_check_ids': [Command.set([check_2.id])]})
        outbound_payment_2.action_post()

        inbound_payment_2.action_post()

        # Check should also not be on hand in this order
        self.assertFalse(
            check_2.current_journal_id,
            "Check should not be on hand even if outbound was created before inbound",
        )

    def test_current_journal_follows_the_date_of_the_operations(self):
        """ The operations are ordered by date first, so editing the date of a confirmed
        payment reorders them and must recompute where the check currently is.
        """
        init_payment = self.create_third_party_check()
        init_payment.date = fields.Date.to_date('2023-11-06')
        check = init_payment.l10n_latam_new_check_ids[0]

        self.env['l10n_latam.payment.mass.transfer'].with_context(
            active_model='l10n_latam.check', active_ids=check.ids,
        ).create({
            'to_journal_id': self.rejected_check_journal.id,
            'payment_date': fields.Date.to_date('2023-11-07'),
        })._create_payments()
        self.assertEqual(check.current_journal_id, self.rejected_check_journal)

        # moving the reception after the transfer makes it the last operation again
        init_payment.date = fields.Date.to_date('2023-11-08')
        self.assertEqual(
            check.current_journal_id, self.third_party_check_journal,
            "The current journal should be recomputed when an operation is moved in time",
        )

    def test_last_operation_with_operations_on_the_same_date(self):
        """ Every operation of a check can be recorded on the same day. In that case the last
        operation is the most recently created one, and editing an older operation afterwards
        must not turn it into the last one.
        """
        init_time = datetime(2023, 11, 6, 8, 0, 0)
        with self.mock_datetime_and_now(init_time):
            init_payment = self.create_third_party_check()
        check = init_payment.l10n_latam_new_check_ids[0]

        transfer_time = init_time + timedelta(hours=1)
        with self.mock_datetime_and_now(transfer_time):
            self.env['l10n_latam.payment.mass.transfer'].with_context(
                active_model='l10n_latam.check', active_ids=check.ids,
            ).create({'to_journal_id': self.rejected_check_journal.id})._create_payments()

        _transfer_out, transfer_in = check.operation_ids.sorted('id')
        self.assertEqual(check._get_last_operation(), transfer_in)
        self.assertEqual(check.current_journal_id, self.rejected_check_journal)

        # editing the payment that received the check should not make it the last operation
        edition_time = transfer_time + timedelta(hours=1)
        with self.mock_datetime_and_now(edition_time):
            init_payment.memo = 'Edited after the check was transferred'

        self.assertEqual(
            check._get_last_operation(), transfer_in,
            "The last operation should be the last one posted, not the last one modified"
        )

    def test_undo_operation_in_the_middle_of_the_check_history(self):
        """ An operation can only be undone when nothing else was done with the check afterwards. """
        init_payment = self.create_third_party_check()
        check = init_payment.l10n_latam_new_check_ids[0]

        outbound_payment = self.env['account.payment'].create({
            'l10n_latam_move_check_ids': check,
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal
                ._get_available_payment_method_lines('outbound')
                .filtered(lambda x: x.code == 'out_third_party_checks').id,
        })
        outbound_payment.action_post()

        with self.assertRaisesRegex(UserError, "moved by a later operation"):
            init_payment.action_draft()

        # the last operation can be undone, and then the reception as well
        outbound_payment.action_draft()
        self.assertEqual(
            check.current_journal_id, self.third_party_check_journal,
            "The check should be back on hand once the delivery is reset",
        )
        init_payment.action_draft()
        self.assertEqual(init_payment.state, 'draft')

    def test_undo_a_whole_chain_of_operations_at_once(self):
        """ Undoing every operation of a check at once is valid: nothing is left dangling. """
        init_payment = self.create_third_party_check()
        check = init_payment.l10n_latam_new_check_ids[0]
        outbound_payment = self.env['account.payment'].create({
            'l10n_latam_move_check_ids': check,
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal
                ._get_available_payment_method_lines('outbound')
                .filtered(lambda x: x.code == 'out_third_party_checks').id,
        })
        outbound_payment.action_post()

        # the whole chain is undone in one go, no operation is left behind a later one
        (init_payment | outbound_payment).action_draft()
        self.assertEqual((init_payment | outbound_payment).mapped('state'), ['draft', 'draft'])

    def test_undo_the_only_operation_of_a_check(self):
        """ A payment that is the sole operation of its checks can always be undone. """
        init_payment = self.create_third_party_check()
        check = init_payment.l10n_latam_new_check_ids[0]
        self.assertEqual(
            check._get_last_operation(), init_payment,
            "The payment that received the check is its only operation",
        )

        init_payment.action_draft()
        self.assertEqual(init_payment.state, 'draft')

        init_payment.action_post()
        init_payment.action_cancel()
        self.assertEqual(init_payment.state, 'canceled')

    def test_undo_a_suffix_of_a_longer_chain(self):
        """ Undoing a trailing part of the chain is valid, undoing operations in its middle is not. """
        init_payment = self.create_third_party_check()
        check = init_payment.l10n_latam_new_check_ids[0]

        def transfer(destination_journal):
            self.env['l10n_latam.payment.mass.transfer'].with_context(
                active_model='l10n_latam.check', active_ids=[check.id],
            ).create({'to_journal_id': destination_journal.id})._create_payments()

        transfer(self.rejected_check_journal)
        transfer(self.third_party_check_journal)

        operations = check._get_operations()
        self.assertEqual(len(operations), 5, "Reception plus two transfers of two payments each")

        # undoing operations that would leave a more recent one behind is refused
        with self.assertRaisesRegex(UserError, "moved by a later operation"):
            operations[:3].action_draft()

        # the three most recent operations can be undone together
        operations[-3:].action_draft()
        self.assertEqual(
            check._get_operations(), operations[:2],
            "Only the operations that were not undone should remain",
        )
        self.assertRecordValues(operations[-3:], [{'state': 'draft'}] * 3)

    def test_check_transfer_between_branches(self):
        """ Checks can be transferred to a sibling branch as long as both branches are activated """
        company = self.company_data_3['company']
        company.write({'child_ids': [
            Command.create({'name': 'AR Branch A'}),
            Command.create({'name': 'AR Branch B'}),
        ]})
        self.cr.precommit.run()  # load the CoA on the branches
        branch_a, branch_b = company.child_ids
        self.env.user.company_ids += company.child_ids

        journal_a = self._create_branch_check_journal(branch_a, 'TPCA')
        journal_b = self._create_branch_check_journal(branch_b, 'TPCB')

        check = self.create_third_party_check(journal=journal_a).l10n_latam_new_check_ids[0]
        self.assertEqual(check.current_journal_id, journal_a)
        self.assertEqual(check.company_id, branch_a)

        wizard = self.env['l10n_latam.payment.mass.transfer'].with_context(
            allowed_company_ids=(branch_a + branch_b).ids,
            active_model='l10n_latam.check',
            active_ids=check.ids,
        ).create({'to_journal_id': journal_b.id})
        wizard._create_payments()
        self.assertEqual(check.current_journal_id, journal_b, 'The check was not moved to the other branch')
        self.assertEqual(check.company_id, branch_b, 'The check should belong to the branch holding it')

        # the check left branch A through an outbound payment and entered branch B through an inbound one
        self.assertRecordValues(check.operation_ids.sorted('payment_type'), [
            {'company_id': branch_b.id, 'payment_type': 'inbound', 'state': 'paid'},
            {'company_id': branch_a.id, 'payment_type': 'outbound', 'state': 'paid'},
        ])
        # both branches share the transfer account of their root company, so the entries are reconciled together
        transfer_lines = check.operation_ids.move_id.line_ids.filtered(
            lambda line: line.account_id == company.transfer_account_id
        )
        self.assertEqual(len(transfer_lines), 2)
        self.assertTrue(all(transfer_lines.mapped('reconciled')))

        # the check can then be delivered by the branch holding it, and stays on it once handed over
        self.env['account.payment'].with_context(allowed_company_ids=branch_b.ids).create({
            'l10n_latam_move_check_ids': [Command.set(check.ids)],
            'partner_id': self.partner_a.id,
            'payment_type': 'outbound',
            'journal_id': journal_b.id,
            'payment_method_line_id': journal_b._get_available_payment_method_lines('outbound').filtered(
                lambda x: x.code in ('out_third_party_checks', 'return_third_party_checks')).id,
        }).action_post()
        self.assertFalse(check.current_journal_id, 'The check is not on hand anymore')
        self.assertEqual(check.company_id, branch_b, 'The check should stay on the branch that delivered it')

    def test_check_transfer_wizard_selection(self):
        """ The wizard refuses to open on a selection that can't be transferred """
        Wizard = self.env['l10n_latam.payment.mass.transfer']
        check = self.create_third_party_check().l10n_latam_new_check_ids[0]

        with self.assertRaisesRegex(ValidationError, 'select the checks'):
            Wizard.with_context(active_model='l10n_latam.check', active_ids=[]).default_get(['to_journal_id'])

        own_check = self._create_own_check()
        with self.assertRaisesRegex(ValidationError, 'not third party checks'):
            Wizard.with_context(
                active_model='l10n_latam.check', active_ids=(check + own_check).ids,
            ).default_get(['to_journal_id'])

        with self.assertRaisesRegex(ValidationError, 'can only be used on third party checks'):
            Wizard.with_context(
                active_model='account.payment', active_ids=check.payment_id.ids,
            ).default_get(['to_journal_id'])

        # opening it on a valid selection gives the journal the checks are currently on
        wizard = Wizard.with_context(
            active_model='l10n_latam.check', active_ids=check.ids,
        ).create({'to_journal_id': self.rejected_check_journal.id})
        self.assertEqual(wizard.check_ids, check)
        self.assertEqual(wizard.from_journal_id, self.third_party_check_journal)

        # the wizard may also be created without the active_ids context, but stays consistent
        with self.assertRaisesRegex(ValidationError, 'transferred from the journal'):
            Wizard.create({
                'check_ids': check.ids,
                'from_journal_id': self.rejected_check_journal.id,
                'to_journal_id': self.rejected_check_journal.id,
            })
        Wizard.create({
            'check_ids': check.ids,
            'from_journal_id': self.third_party_check_journal.id,
            'to_journal_id': self.rejected_check_journal.id,
        })._create_payments()
        self.assertEqual(check.current_journal_id, self.rejected_check_journal)

    def test_check_transfer_between_branches_without_common_transfer_account(self):
        """ Nothing is created when the branches don't share their Inter-Banks Transfer Account """
        company = self.company_data_3['company']
        company.write({'child_ids': [Command.create({'name': 'AR Branch C'})]})
        self.cr.precommit.run()  # load the CoA on the branch
        branch = company.child_ids
        self.env.user.company_ids += branch
        branch.transfer_account_id = self.env['account.account'].create({
            'name': 'Branch Transfer Account',
            'code': 'TRANSFC',
            'account_type': 'asset_current',
            'company_ids': [Command.set(branch.ids)],
        })

        check = self.create_third_party_check().l10n_latam_new_check_ids[0]
        wizard = self.env['l10n_latam.payment.mass.transfer'].with_context(
            allowed_company_ids=(company + branch).ids,
            active_model='l10n_latam.check',
            active_ids=check.ids,
        ).create({'to_journal_id': self._create_branch_check_journal(branch, 'TPCC').id})

        payment_count = self.env['account.payment'].search_count([])
        with self.assertRaisesRegex(UserError, 'Inter-Banks Transfer Account'):
            wizard._create_payments()
        self.assertEqual(self.env['account.payment'].search_count([]), payment_count, 'No payment should have been created')

    def test_same_check_number_allowed_for_new_third_party_checks(self):
        """Ensure that the same check number can be used for New Third Party Checks payments."""
        payment = self.create_third_party_check()

        check = payment.l10n_latam_new_check_ids[0]

        second_payment = self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'payment_type': 'inbound',
            'journal_id': self.third_party_check_journal.id,
            'payment_method_line_id': self.third_party_check_journal._get_available_payment_method_lines('inbound').filtered(lambda x: x.code == 'new_third_party_checks').id,
            'amount': 1,
            'l10n_latam_new_check_ids': [
                Command.create({
                    'name': check.name,
                    'amount': 1,
                    'payment_date': fields.Date.add(fields.Date.today(), months=1),
                }),
            ],
        })
        second_payment.action_post()
        self.assertFalse(
            second_payment.l10n_latam_new_check_ids.outstanding_line_id,
            "Posting a second payment with the same check number for New Third Party Checks should be allowed.",
        )
