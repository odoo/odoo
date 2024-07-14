# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.addons.account_consolidation.report.handler.abstract import AbstractHandler
from odoo.addons.account_consolidation.report.handler.journals import JournalsHandler
from odoo.addons.account_consolidation.report.handler.periods import PeriodsHandler
from odoo.addons.account_consolidation.report.handler.show_zero import ShowZeroHandler
from odoo.addons.account_consolidation.tests.account_consolidation_test_classes import AccountConsolidationTestCase

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestAbstractHandler(TransactionCase):
    """
    Tested with a PeriodBuilder as AbstractBuilder is abstract
    """

    @patch('odoo.addons.account_consolidation.report.handler.abstract.AbstractHandler.get_selected_values')
    def test__is_set(self, patched):
        combinations = (
            ([], False),
            ([1], True),
            ([1, 1], True)
        )
        for val, expect in combinations:
            patched.return_value = val
            self.assertEqual(AbstractHandler.is_set({}), expect)
            patched.asset_called_once_with({})
            patched.reset_mock()


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestJournalHandler(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()
        self.handler = JournalsHandler(self.env)
        self.ap = self._create_analysis_period()
        self.journal = self.env['consolidation.journal'].create({
            'name': 'blah',
            'period_id': self.ap.id,
            'chart_id': self.chart.id,
        })

    @patch('odoo.addons.account_consolidation.report.handler.periods.PeriodsHandler.is_set')
    @patch('odoo.addons.account_consolidation.report.handler.journals.JournalsHandler.get_option_values')
    def test_handle(self, patched_options, patched_isset):
        patched_options.return_value = [{'id': 1, 'selected': True}, {'id': 2, 'selected': False}]
        patched_isset.return_value = True
        client_state = {'dummy': 42}
        base_period = self.ap
        current_options = {'gameof': 'thrones'}
        out = self.handler.handle(client_state, base_period, current_options)
        self.assertEqual(out, patched_options.return_value)
        patched_isset.assert_called_once_with(current_options)
        patched_options.assert_called_once_with(base_period, {})

        patched_options.reset_mock()
        patched_isset.reset_mock()
        patched_isset.return_value = False

        out = self.handler.handle(client_state, base_period, current_options)
        self.assertEqual(out, patched_options.return_value)
        patched_isset.assert_called_once_with(current_options)
        patched_options.assert_called_once_with(base_period, client_state)

    def test__get_selected_values(self):
        self.assertListEqual(JournalsHandler.get_selected_values({}), [])
        options = {
            'consolidation_journals': [
                {
                    'id': 1,
                    'name': 'BLAH',
                    'selected': False
                }, {
                    'id': 2,
                    'name': 'BLUH',
                    'selected': True
                }
            ]
        }
        self.assertListEqual(JournalsHandler.get_selected_values(options), [2])
        options['consolidation_journals'][1]['selected'] = False
        self.assertListEqual(JournalsHandler.get_selected_values(options), [1, 2])

    def test__get_selected_values_no_key_in_options(self):
        options = {'blah': 'bluh'}
        self.assertListEqual(JournalsHandler.get_selected_values(options), [])

    def test__get_option_values(self):
        res = self.handler.get_option_values(self.ap, {})
        journal_option = {
            'id': self.journal.id,
            'name': self.journal.name,
            'selected': False
        }
        expected = [journal_option]
        self.assertListEqual(res, expected)
        journal_option['selected'] = True
        res = self.handler.get_option_values(self.ap, [journal_option])
        self.assertListEqual(res, expected)

    def test_to_option_dict(self):
        selected = True
        exp = {
            'id': self.journal.id,
            'name': self.journal.name,
            'selected': selected
        }
        res = self.handler.to_option_dict(self.journal, selected)
        self.assertDictEqual(res, exp)


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestPeriodsHandler(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()
        self.periods_handler = PeriodsHandler(self.env)

    def test__get_selected_values(self):
        options = {'periods': [
            {
                'id': 1,
                'name': 'bluh',
                'selected': True
            },
            {
                'id': 2,
                'name': 'blah',
                'selected': False
            },
            {
                'id': 3,
                'name': 'bleh',
                'selected': True
            },
        ]}
        res = self.periods_handler.get_selected_values(options)
        self.assertListEqual(res, [1, 3])

    def test__get_selected_values_no_key_in_options(self):
        options = {'blah': 'bluh'}
        res = self.periods_handler.get_selected_values(options)
        self.assertListEqual(res, [])

    @patch('odoo.addons.account_consolidation.report.handler.periods.PeriodsHandler.get_selected_values',
           return_value=[1, 3])
    def test_to_option_dict(self, patched_method):
        ap = self._create_analysis_period()
        sel_period_ids = self.periods_handler.get_selected_values({})
        opt_dict = self.periods_handler._to_option_dict(ap, sel_period_ids)
        self.assertEqual(ap.id in patched_method.return_value, opt_dict['selected'])
        self.assertEqual(ap.id, opt_dict['id'])
        self.assertEqual(f'{ap.display_name} ({ap.display_dates})', opt_dict['name'])

    def test_handle(self):
        base_period = self._create_analysis_period(start_date="2019-02-01", end_date="2019-02-28")
        previous_period = self._create_analysis_period(start_date="2019-01-01", end_date="2019-01-31")
        pprevious_period = self._create_analysis_period(start_date="2018-12-01", end_date="2018-12-31")
        initial_client_state = None
        first_handle_result = self.periods_handler.handle(initial_client_state, base_period, {})
        self.assertIn(self.periods_handler._to_option_dict(pprevious_period, []), first_handle_result)
        self.assertIn(self.periods_handler._to_option_dict(previous_period, []), first_handle_result)

        # Second handle result
        client_state = [
            self.periods_handler._to_option_dict(pprevious_period, [previous_period.id]),
            self.periods_handler._to_option_dict(previous_period, [previous_period.id])
        ]
        second_handle_result = self.periods_handler.handle(client_state, base_period, {})
        for client_state_line in client_state:
            self.assertIn(client_state_line, second_handle_result)


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestShowZeroHandler(AccountConsolidationTestCase):
    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler._line_is_not_zero')
    def test_account_line_should_be_added(self, patched_line_not_zero):
        will_be_ignored = {}
        options_enabled = {'consolidation_show_zero_balance_accounts': True}
        options_disabled = {'consolidation_show_zero_balance_accounts': False}
        self.assertTrue(ShowZeroHandler.account_line_should_be_added(will_be_ignored, options_enabled))
        patched_line_not_zero.assert_not_called()

        possible_values = (False, True)
        for patched_value in possible_values:
            patched_line_not_zero.reset_mock()
            patched_line_not_zero.return_value = patched_value
            self.assertEqual(ShowZeroHandler.account_line_should_be_added(will_be_ignored, None), patched_value)
            self.assertEqual(ShowZeroHandler.account_line_should_be_added(will_be_ignored, {}), patched_value)
            self.assertEqual(ShowZeroHandler.account_line_should_be_added(will_be_ignored, options_disabled),
                             patched_value)
            self.assertEqual(patched_line_not_zero.call_count, 3)

    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler._section_line_is_not_zero')
    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler._section_line_has_children')
    def test_section_line_should_be_added(self, patched_children, patched_zero):
        will_be_ignored = []
        options_enabled = {'consolidation_show_zero_balance_accounts': True}
        options_disabled = {'consolidation_show_zero_balance_accounts': False}
        self.assertTrue(ShowZeroHandler.section_line_should_be_added(will_be_ignored, None))
        patched_children.assert_not_called()
        patched_zero.assert_not_called()
        self.assertTrue(ShowZeroHandler.section_line_should_be_added(will_be_ignored, options_enabled))
        patched_children.assert_not_called()
        patched_zero.assert_not_called()

        combination_values = [(False, True, True), (False, False, False), (True, False, True), (True, True, True)]
        for pc_value, pz_value, exp_value in combination_values:
            patched_children.reset_mock()
            patched_zero.reset_mock()
            patched_children.return_value = pc_value
            patched_zero.return_value = pz_value
            self.assertEqual(ShowZeroHandler.section_line_should_be_added(will_be_ignored, {}), exp_value)
            self.assertEqual(ShowZeroHandler.section_line_should_be_added(will_be_ignored, options_disabled), exp_value)
            self.assertEqual(patched_children.call_count, 2)
            # lazy evaluation : patched_children will always be called but not patched_zero
            # (not called if patched children is true)
            self.assertEqual(patched_zero.call_count, 0 if pc_value else 2)

    def test__line_is_not_zero(self):
        test_lines = [
            ({'columns': []}, False),
            ({'columns': [{'no_format': 0.0}]}, False),
            ({'columns': [{'no_format': 42.42}]}, True),
            ({'columns': [{'no_format': 42.42}, {'no_format': 0}]}, True),
            ({'columns': [{'no_format': 0}, {'no_format': 42.42}]}, True),
            ({'columns': [{'no_format': -42.424242}, {'no_format': 42.424242}]}, False),
        ]
        for line in test_lines:
            self.assertEqual(ShowZeroHandler._line_is_not_zero(line[0]), line[1],
                             "line_is_not_zero(%s) should be %s" % (line[0], line[1]))

    def test__section_line_has_children(self):
        self.assertFalse(ShowZeroHandler._section_line_has_children([]))
        self.assertFalse(ShowZeroHandler._section_line_has_children([{'id': 'section-1'}]))
        self.assertTrue(ShowZeroHandler._section_line_has_children([{'id': 'section-1'}, {'id': 1}]))

    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler._line_is_not_zero')
    def test__section_line_is_not_zero(self, patched):
        patched.return_value = False
        empty = []
        only_sect = [{'id': 'section-1'}]
        sect_and_acc = [{'id': 'section-1'}, {'id': 'account-1'}]
        self.assertFalse(ShowZeroHandler._section_line_is_not_zero(empty))
        patched.assert_not_called()
        self.assertFalse(ShowZeroHandler._section_line_is_not_zero(only_sect))
        self.assertFalse(ShowZeroHandler._section_line_is_not_zero(sect_and_acc))
        patched.assert_called_with(only_sect[0])
        patched.assert_called_with(sect_and_acc[0])

        patched.reset_mock()
        patched.return_value = True
        self.assertFalse(ShowZeroHandler._section_line_is_not_zero(empty))
        patched.assert_not_called()
        self.assertTrue(ShowZeroHandler._section_line_is_not_zero(only_sect))
        self.assertTrue(ShowZeroHandler._section_line_is_not_zero(sect_and_acc))
        patched.assert_called_with(only_sect[0])
        patched.assert_called_with(sect_and_acc[0])
