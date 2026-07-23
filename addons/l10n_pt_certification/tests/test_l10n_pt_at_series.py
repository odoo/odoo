from psycopg2.errors import UniqueViolation

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import freeze_time
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@freeze_time('2024-06-15')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtAtSeries(TestL10nPtCommon):

    def test_name_and_prefix_must_be_alphanumeric(self):
        # Cannot have a non-alphanumeric name
        with self.assertRaises(ValidationError):
            self.env['l10n_pt.at.series'].create({
                'name': '2025\nBad',
                'company_id': self.company_pt.id,
                'date_start': '2025-01-01',
                'journal_id': self.company_data['default_journal_sale'].id,
                'document_type': 'out_invoice',
                'prefix': 'INV',
            })

        # Cannot have a non-alphanumeric prefix
        with self.assertRaises(ValidationError):
            self.env['l10n_pt.at.series'].create({
                'name': '2025',
                'company_id': self.company_pt.id,
                'date_start': '2025-01-01',
                'journal_id': self.company_data['default_journal_sale'].id,
                'document_type': 'out_invoice',
                'prefix': 'INV!',
            })

    def test_unique_constraints_per_company(self):
        series_24 = self.series_2024[0]

        with mute_logger('odoo.sql_db'):
            # The name + document type must be unique per company
            with self.assertRaises(UniqueViolation):
                self.env['l10n_pt.at.series'].create({
                    'name': series_24.name,
                    'document_type': series_24.document_type,
                    'company_id': series_24.company_id.id,
                    'date_start': series_24.date_start,
                    'journal_id': series_24.journal_id.id,
                    'prefix': 'NEWINV',
                    'at_code': 'RANDOM1234',
                })

            # The prefix + name must be unique per company
            with self.assertRaises(UniqueViolation):
                self.env['l10n_pt.at.series'].create({
                    'name': series_24.name,
                    'document_type': 'debit_note',
                    'company_id': series_24.company_id.id,
                    'date_start': series_24.date_start,
                    'journal_id': series_24.journal_id.id,
                    'prefix': series_24.prefix,
                    'at_code': 'RANDOM1234',
                })

            # AT code must be unique
            with self.assertRaises(UniqueViolation):
                self.env['l10n_pt.at.series'].create({
                    'name': 'NEWNAME',
                    'document_type': series_24.document_type,
                    'company_id': series_24.company_id.id,
                    'date_start': series_24.date_start,
                    'journal_id': series_24.journal_id.id,
                    'prefix': 'NEWINV',
                    'at_code': series_24.at_code,
                })

        # We can create the same document type with different name and AT code
        self.env['l10n_pt.at.series'].create({
                'name': 'NEWNAME',
                'document_type': series_24.document_type,
                'company_id': series_24.company_id.id,
                'date_start': series_24.date_start,
                'journal_id': series_24.journal_id.id,
                'prefix': series_24.prefix,
                'at_code': 'RANDOM1234',
            })

    def test_active_computed_from_date_range_and_correct_search(self):
        # remove all existing series
        self.env['l10n_pt.at.series'].with_context(active_test=False).search([]).unlink()

        # Past and future series should be inactive
        future_series = self.env['l10n_pt.at.series'].create({
            'name': '2099',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2099-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'FUT',
        })
        past_series = self.env['l10n_pt.at.series'].create({
            'name': '2020',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2020-01-01',
            'date_end': '2020-12-31',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'PST',
        })
        self.assertFalse(future_series.active)
        self.assertFalse(past_series.active)

        # If today is within range of series, then series is active
        active_series_mid_range = self.env['l10n_pt.at.series'].create([{
            'name': '2024',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2024-01-01',
            'date_end': '2024-12-31',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'INV',
            'at_code': 'AT-TESTINV2024',
        }])
        active_series_start_range = active_series_mid_range.copy({
            'name': 'start202406',
            'date_start': '2024-06-15',
            'at_code': 'AT-start1234',
        })
        active_series_end_range = active_series_mid_range.copy({
            'name': 'end202406',
            'date_end': '2024-06-15',
            'at_code': 'AT-end1234',
        })
        active_series_no_end = active_series_mid_range.copy({
            'name': 'noend202406',
            'date_end': '',
            'at_code': 'AT-noend1234',
        })
        self.assertTrue(active_series_mid_range.active)
        self.assertTrue(active_series_start_range.active)
        self.assertTrue(active_series_end_range.active)
        self.assertTrue(active_series_no_end.active)

        # All 4 queries are equivalent (should return the active series only)
        active_series_1 = self.env['l10n_pt.at.series'].search([('active', '=', True)])
        active_series_2 = self.env['l10n_pt.at.series'].search([('active', 'in', (True,))])
        active_series_3 = self.env['l10n_pt.at.series'].search([('active', '!=', False)])
        active_series_4 = self.env['l10n_pt.at.series'].search([('active', 'not in', (False,))])

        self.assertEqual(len(active_series_1), 4)
        self.assertEqual(
            active_series_1 | active_series_2 | active_series_3 | active_series_4,
            active_series_mid_range + active_series_start_range + active_series_end_range + active_series_no_end,
        )

        # All 4 queries are equivalent (should return the inactive series only)
        inactive_series_1 = self.env['l10n_pt.at.series'].search([('active', '=', False)])
        inactive_series_2 = self.env['l10n_pt.at.series'].search([('active', 'in', (False,))])
        inactive_series_3 = self.env['l10n_pt.at.series'].search([('active', '!=', True)])
        inactive_series_4 = self.env['l10n_pt.at.series'].search([('active', 'not in', (True,))])

        self.assertEqual(len(inactive_series_1), 2)
        self.assertEqual(
            inactive_series_1 | inactive_series_2 | inactive_series_3 | inactive_series_4,
            future_series + past_series,
        )

    def test_write_delete_protection_when_used_in_posted_moves(self):
        series = self.env['l10n_pt.at.series'].create({
            'name': '2024ZW',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2024-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'ZXX',
        })
        self.env['account.move'].with_company(self.company_pt).create({
            'company_id': self.company_pt.id,
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-06-01',
            'l10n_pt_at_series_id': series.id,
            'line_ids': [
                Command.create({
                    'name': 'Product',
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [self.tax_sale_23.id],
                }),
            ],
        }).action_post()

        # Fields should be protected since invoice is posted
        protected_test_cases = [
            ('prefix', 'INV'),
            ('name', '2024RANDOM'),
            ('document_type', 'debit_note'),
            ('date_start', '2024-06-01'),
            ('date_end', '2024-06-01'),
            ('training_series', False),
            ('journal_id', self.company_data['default_journal_sale'].id),
            ('company_exclusive_series', False),
            ('company_id', self.env.company.id),
        ]
        for field, value in protected_test_cases:
            with self.assertRaisesRegex(UserError, "You cannot change the properties of a series that has already been used by a journal entry."):
                series.write({field: value})

        # Since series doesn't have an AT code, we can set it (even if invoice is posted)
        series.write({'at_code': 'AT-ZXX2024ZW'})
        # After it's set, it cannot be changed
        with self.assertRaisesRegex(UserError, "You cannot change the AT Validation Code of a series that has already been used."):
            series.write({'at_code': 'AT-ZXX2024ZWZ'})

        # Cannot delete a series being used by a posted invoice
        with self.assertRaisesRegex(UserError, "You cannot delete a series that is used. It will automatically be archived after the End Date"):
            series.unlink()

    def test_get_at_code_raises_when_inactive(self):
        inactive_series = self.env['l10n_pt.at.series'].create({
            'name': '2020A',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2020-01-01',
            'date_end': '2020-12-31',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'INA',
            'at_code': 'AT-INA2020A',
        })
        with self.assertRaisesRegex(UserError, "The series.*is not active."):
            inactive_series._get_at_code()

    def test_journal_required_for_different_documents(self):
        with self.assertRaisesRegex(ValidationError, "A Payment Journal is required when you have Payment Receipt lines."):
            self.env['l10n_pt.at.series'].create({
                'name': '2025P',
                'company_id': self.company_pt.id,
                'training_series': True,
                'date_start': '2025-01-01',
                'document_type': 'payment_receipt',
                'prefix': 'PAYX',
            })
        with self.assertRaisesRegex(ValidationError, "A Sales Journal is required for account move document types.*"):
            self.env['l10n_pt.at.series'].create({
                'name': '2025S',
                'company_id': self.company_pt.id,
                'training_series': True,
                'date_start': '2025-01-01',
                'document_type': 'out_invoice',
                'prefix': 'SALEX',
            })

    def test_document_number_sequence_created_and_reused(self):
        series = self.env['l10n_pt.at.series'].create({
            'name': '2025Q',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'SEQ',
            'at_code': 'AT-SEQ2025Q',
        })
        # Document identifier computed from prefix and name
        self.assertEqual(series.document_identifier, 'SEQ 2025Q')

        seq1 = series._l10n_pt_get_document_number_sequence()
        seq2 = series._l10n_pt_get_document_number_sequence()
        self.assertEqual(seq1, seq2)
        self.assertEqual(seq1.implementation, 'no_gap')

    def test_company_exclusive_onchange_does_not_crash(self):
        series = self.env['l10n_pt.at.series'].create({
            'name': '2025E',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'EXC',
            'at_code': 'AT-EXC2025E',
        })
        series.company_exclusive_series = True
        series._onchange_company_exclusive_series()
        series.company_exclusive_series = False
        series._onchange_company_exclusive_series()
