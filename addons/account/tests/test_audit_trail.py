import logging

from odoo.addons.account.tests.common import AccountTestInvoicingCommon, AccountTestInvoicingHttpCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.api import SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged, new_test_user

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'mail_track')
class TestAuditTrail(AccountTestInvoicingCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env['base'].with_context(
            tracking_disable=False,
            mail_create_nolog=False,
            mail_notrack=False,
        ).env
        cls.env.company.restrictive_audit_trail = False
        cls.move = cls.create_move()

    @classmethod
    def create_move(cls):
        return cls.env['account.move'].create({
            'date': '2021-04-01',
            'line_ids': [
                Command.create({
                    'balance': 100,
                    'account_id': cls.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'balance': -100,
                    'account_id': cls.company_data['default_account_revenue'].id
                }),
            ],
        })

    def get_trail(self, record):
        self.env.cr.precommit.run()
        return self.env['mail.message'].search([
            ('model', '=', record._name),
            ('res_id', '=', record.id),
        ])

    def assertTrail(self, trail, expected):
        self.assertEqual(len(trail), len(expected))
        for message, expected_needle in zip(trail, expected[::-1]):
            self.assertIn(expected_needle, message.account_audit_log_preview)

    def test_can_unlink_draft(self):
        self.env.company.restrictive_audit_trail = True
        self.move.unlink()

    def test_cant_unlink_posted(self):
        self.env.company.restrictive_audit_trail = True
        self.move.action_post()
        self.move.button_draft()
        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail"):
            self.move.unlink()

    def test_cant_unlink_message(self):
        self.env.company.restrictive_audit_trail = True
        self.move.action_post()
        self.env.cr.flush()
        audit_trail = self.get_trail(self.move)
        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail"):
            audit_trail.unlink()

    def test_cant_unown_message(self):
        self.env.company.restrictive_audit_trail = True
        self.move.action_post()
        self.env.cr.flush()
        audit_trail = self.get_trail(self.move)
        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail"):
            audit_trail.res_id = 0

    def test_cant_unlink_tracking_value(self):
        self.env.company.restrictive_audit_trail = True
        self.move.action_post()
        self.env.cr.precommit.run()
        with self.mock_mail_gateway(), self.mock_mail_app():
            self.move.name = 'track this!'
            self.flush_tracking()
        audit_trail = self._new_msgs
        self.assertMessageFields(
            audit_trail, {
                'body': '',
                'tracking_values': [
                    ('name', 'char', 'MISC/2021/04/0001', 'track this!'),
                ],
            }
        )
        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail"):
            audit_trail.unlink()

    def test_content(self):
        with self.mock_mail_gateway(), self.mock_mail_app():
            move = self.create_move()
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'body': '<p>Journal Entry created</p>',
                'message_type': 'notification',
                'tracking_values': [],
            }
        )

        with self.mock_mail_gateway(), self.mock_mail_app():
            move.action_post()
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'account_audit_log_preview': 'Updated\nFalse ⇨ MISC/2021/04/0001 (Number)\nDraft ⇨ Posted (Status)',
                'body': '',
                'message_type': 'notification',
                'tracking_values': [
                    ('name', 'char', False, 'MISC/2021/04/0001'),
                    ('state', 'selection', 'Draft', 'Posted'),
                ],
            }
        )

        with self.mock_mail_gateway(), self.mock_mail_app():
            move.button_draft()
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'account_audit_log_preview': 'Updated\nPosted ⇨ Draft (Status)',
                'body': '',
                'message_type': 'notification',
                'tracking_values': [
                    ('state', 'selection', 'Posted', 'Draft'),
                ],
            }
        )

        with self.mock_mail_gateway(), self.mock_mail_app():
            move.name = "nawak"
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'account_audit_log_preview': 'Updated\nMISC/2021/04/0001 ⇨ nawak (Number)',
                'body': '',
                'message_type': 'notification',
                'tracking_values': [
                    ('name', 'char', 'MISC/2021/04/0001', 'nawak'),
                ],
            }
        )

        with self.mock_mail_gateway(), self.mock_mail_app():
            move.line_ids = [
                Command.update(move.line_ids[0].id, {'balance': 300}),
                Command.update(move.line_ids[1].id, {'credit': 200}),  # writing on debit/credit or balance both log
                Command.create({
                    'balance': -100,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ]
            self.flush_tracking()
        for msg, check_values in zip(self._new_msgs, [
            # update 1
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[0].id} updated\n100.0 ⇨ 300.0 (Balance)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[0].id}">#{move.line_ids[0].id}</a> updated</p>',
                'tracking_values': [('balance', 'monetary', 100, (300, self.env.ref('base.USD')))],
            },
            # update 2
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[1].id} updated\n-100.0 ⇨ -200.0 (Balance)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[1].id}">#{move.line_ids[1].id}</a> updated</p>',
                'tracking_values': [('balance', 'monetary', -100, (-200, self.env.ref('base.USD')))],
            },
            # new line
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[2].id} created\n ⇨ 400000 Product Sales (Account)\n0.0 ⇨ -100.0 (Balance)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[2].id}">#{move.line_ids[2].id}</a> created</p>',
                'tracking_values': [
                    ('balance', 'monetary', 0, (-100, self.env.ref('base.USD'))),
                    ('account_id', 'many2one', False, self.company_data['default_account_revenue']),
                ],
            },
        ], strict=True):
            self.assertMessageFields(
                msg, {
                    'message_type': 'notification',
                    **check_values,
                }
            )

        with self.mock_mail_gateway(), self.mock_mail_app():
            move.line_ids[0].tax_ids = self.env.company.account_purchase_tax_id
            self.flush_tracking()
        suspense_account = self.env.company.account_journal_suspense_account_id
        for msg, check_values in zip(self._new_msgs, [
            # update 1
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[0].id} updated\n ⇨ 15% (Taxes)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[0].id}">#{move.line_ids[0].id}</a> updated</p>',
                'tracking_values': [('tax_ids', 'many2many', '', '15%')],
            },
            # new line
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[3].id} created\n ⇨ 131000 Tax Paid (Account)\n0.0 ⇨ 45.0 (Balance)\nFalse ⇨ 15% (Label)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[3].id}">#{move.line_ids[3].id}</a> created</p>',
                'tracking_values': [
                    ('name', 'char', False, '15%'),
                    ('balance', 'monetary', 0, (45, self.env.ref('base.USD'))),
                    ('account_id', 'many2one', False, self.company_data['default_account_tax_purchase']),
                ],
            },
            # new line
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[4].id} created\n ⇨ {suspense_account.code} Bank Suspense Account (Account)\n0.0 ⇨ -45.0 (Balance)\nFalse ⇨ Automatic Balancing Line (Label)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[4].id}">#{move.line_ids[4].id}</a> created</p>',
                'tracking_values': [
                    ('name', 'char', False, "Automatic Balancing Line"),
                    ('balance', 'monetary', 0, (-45, self.env.ref('base.USD'))),
                    ('account_id', 'many2one', False, suspense_account),
                ],
            },
        ], strict=True):
            self.assertMessageFields(
                msg, {
                    'message_type': 'notification',
                    **check_values,
                }
            )

        exp_results = [
            {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[0].id} deleted\n400000 Product Sales ⇨  (Account)\n300.0 ⇨ 0.0 (Balance)\n15% ⇨  (Taxes)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[0].id}">#{move.line_ids[0].id}</a> deleted</p>',
                'tracking_values': [
                    ('account_id', 'many2one', self.company_data['default_account_revenue'], False),
                    ('balance', 'monetary', 300, (0, self.env['res.currency'])),
                    ('tax_ids', 'many2many', '15%', ''),
                ],
            }, {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[1].id} deleted\n400000 Product Sales ⇨  (Account)\n-200.0 ⇨ 0.0 (Balance)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[1].id}">#{move.line_ids[1].id}</a> deleted</p>',
                'tracking_values': [
                    ('account_id', 'many2one', self.company_data['default_account_revenue'], False),
                    ('balance', 'monetary', -200, (0, self.env['res.currency'])),
                ],
            }, {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[2].id} deleted\n400000 Product Sales ⇨  (Account)\n-100.0 ⇨ 0.0 (Balance)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[2].id}">#{move.line_ids[2].id}</a> deleted</p>',
                'tracking_values': [
                    ('account_id', 'many2one', self.company_data['default_account_revenue'], False),
                    ('balance', 'monetary', -100, (0, self.env['res.currency'])),
                ],
            }, {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[3].id} deleted\n131000 Tax Paid ⇨  (Account)\n45.0 ⇨ 0.0 (Balance)\n15% ⇨ False (Label)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[3].id}">#{move.line_ids[3].id}</a> deleted</p>',
                'tracking_values': [
                    ('account_id', 'many2one', self.company_data['default_account_tax_purchase'], False),
                    ('balance', 'monetary', 45, (0, self.env['res.currency'])),
                    ('name', 'char', '15%', False),
                ],
            }, {
                'account_audit_log_preview': f'Journal Item #{move.line_ids[4].id} deleted\n{suspense_account.code} Bank Suspense Account ⇨  (Account)\n-45.0 ⇨ 0.0 (Balance)\nAutomatic Balancing Line ⇨ False (Label)',
                'body': f'<p>Journal Item <a href="#" data-oe-model="account.move.line" data-oe-id="{move.line_ids[4].id}">#{move.line_ids[4].id}</a> deleted</p>',
                'tracking_values': [
                    ('account_id', 'many2one', suspense_account, False),
                    ('balance', 'monetary', -45, (-0, self.env['res.currency'])),
                    ('name', 'char', "Automatic Balancing Line", False),
                ],
            },
        ]
        with self.mock_mail_gateway(), self.mock_mail_app():
            move.with_context(dynamic_unlink=True).line_ids.unlink()
            self.flush_tracking()
        for msg, check_values in zip(self._new_msgs, exp_results, strict=True):
            self.assertMessageFields(
                msg, {
                    'message_type': 'notification',
                    **check_values,
                }
            )

        with self.mock_mail_gateway(), self.mock_mail_app():
            self.env.company.restrictive_audit_trail = True
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'account_audit_log_preview': 'Updated\nFalse ⇨ True (Restrictive Audit Trail)',
                'body': '',
                'message_type': 'notification',
                'tracking_values': [('restrictive_audit_trail', 'boolean', False, True)],
            }
        )

    def test_partner_notif(self):
        """Audit trail should not block partner notification."""
        user = new_test_user(
            self.env, 'test-user-notif', groups="base.group_portal",
            notification_type='email',
        )
        # identify that user as being a customer
        user.partner_id.sudo().customer_rank += 1
        self.assertGreater(user.partner_id.customer_rank, 0)
        user.partner_id.message_post(body='Test', partner_ids=user.partner_id.ids)

    def test_partner_unlink(self):
        """Audit trail should not block partner unlink if they didn't create moves"""
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'customer_rank': 1,
        })
        partner.unlink()

    def test_unauthorized_account_audit_trail(self):
        account = (
            self.env['account.account']
            .with_user(SUPERUSER_ID)
            .create({'name': 'foo', 'code': '111111'})
            .with_user(self.env.user)
        )
        account.invalidate_recordset()
        self.env['mail.message'].sudo().create({
            'model': 'account.account',
            'res_id': account.id,
            'body': 'lolo a vu le fifi de papa',
            'author_id': self.partner.id,
            'message_type': 'notification',
        })
        # similar to domain in action_account_audit_trail_report
        # should raise no error when the user access it
        self.env['mail.message'].search([
            ('message_type', '=', 'notification'),
            ('model', '=', 'account.account'),
        ])


@tagged('post_install', '-at_install')
class TestAuditTrailAttachment(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.restrictive_audit_trail = True
        cls.document_installed = 'documents_account' in cls.env['ir.module.module']._installed()
        if cls.document_installed:
            folder_test = cls.env['documents.document'].create({
                'name': 'folder_test',
                'type': 'folder',
            })
            existing_setting = cls.env['documents.account.folder.setting'].sudo().search(
                [('journal_id', '=', cls.company_data['default_journal_sale'].id)])
            if existing_setting:
                existing_setting.folder_id = folder_test
            else:
                cls.env['documents.account.folder.setting'].sudo().create({
                    'folder_id': folder_test.id,
                    'journal_id': cls.company_data['default_journal_sale'].id,
                })

    def _send_and_print(self, invoice):
        return self.env['account.move.send'].with_context(
            force_report_rendering=True,
        )._generate_and_send_invoices(invoice)

    def test_audit_trail_attachment(self):
        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'product',
                'quantity': 1,
                'price_unit': 100,
            })],
        }])
        invoice.action_post()
        self.assertFalse(invoice.message_main_attachment_id)

        # Print the invoice for the first time
        first_attachment = self._send_and_print(invoice)
        self.assertTrue(first_attachment)

        # Remove the attachment, it should only archive it instead of deleting it
        first_attachment.unlink()
        self.assertTrue(first_attachment.exists())
        # But we cannot entirely remove it
        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail."):
            first_attachment.unlink()

        # Print a second time the invoice, it generates a new attachment
        invoice.invalidate_recordset()
        second_attachment = self._send_and_print(invoice)
        self.assertNotEqual(first_attachment, second_attachment)

        # Make sure we can browse all the attachments in the UI (as it changes the main attachment)
        first_attachment.register_as_main_attachment()
        self.assertEqual(invoice.message_main_attachment_id, first_attachment)
        second_attachment.register_as_main_attachment()
        self.assertEqual(invoice.message_main_attachment_id, second_attachment)

        if self.document_installed:
            # Make sure we can change the version history of the document
            document = self.env['documents.document'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('name', '=ilike', '%.pdf'),
            ])
            self.assertTrue(document)
            document.attachment_id = first_attachment
            document.attachment_id = second_attachment
        else:
            _logger.runbot("Documents module is not installed, skipping part of the test")

    def test_audit_trail_write_attachment(self):
        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'product',
                'quantity': 1,
                'price_unit': 100,
            })],
        }])
        invoice.action_post()
        self.assertFalse(invoice.message_main_attachment_id)

        # Print the invoice for the first time
        self._send_and_print(invoice)
        attachment = invoice.message_main_attachment_id

        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail."):
            attachment.write({
                'res_id': self.env.user.id,
                'res_model': self.env.user._name,
            })

        with self.assertRaisesRegex(UserError, "remove parts of a restricted audit trail."):
            attachment.raw = b'new data'

        # Adding an attachment to the log notes should be allowed
        another_attachment = self.env['ir.attachment'].create({
            'name': 'doc.pdf',
            'res_model': 'mail.compose.message',
            # Ensures a bytes-like object with guessed mimetype = 'application/pdf' (checked in _except_audit_trail())
            'datas': attachment.datas,
        })
        invoice.message_post(message_type='comment', attachment_ids=another_attachment.ids)
