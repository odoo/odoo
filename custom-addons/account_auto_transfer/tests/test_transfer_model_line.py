# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.addons.account_auto_transfer.tests.account_auto_transfer_test_classes import AccountAutoTransferTestCase

from odoo import fields
from odoo.tests import tagged

# ############################################################################ #
#                                UNIT TESTS                                    #
# ############################################################################ #
@tagged('post_install', '-at_install')
class MoveModelLineTestCase(AccountAutoTransferTestCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls._assign_origin_accounts(cls)

    def test__get_transfer_move_lines_values_same_aaccounts(self):
        amounts = [4242.42, 1234.56]
        aaccounts = [self._create_analytic_account('ANAL0' + str(i)) for i in range(2)]
        self._create_basic_move(
            cred_account=self.destination_accounts[0].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[0],
            deb_analytic=aaccounts[0].id
        )
        self._create_basic_move(
            cred_account=self.destination_accounts[1].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[1],
            deb_analytic=aaccounts[1].id
        )
        transfer_model_line_1 = self._add_transfer_model_line(self.destination_accounts[0].id,
                                                      analytic_account_ids=[aaccounts[0].id, aaccounts[1].id])
        transfer_model_line_2 = self._add_transfer_model_line(self.destination_accounts[1].id,
                                                      analytic_account_ids=[aaccounts[0].id])

        transfer_models_lines = transfer_model_line_1 + transfer_model_line_2
        args = [fields.Date.to_date('2019-01-01'), fields.Date.to_date('2019-12-19')]
        res = transfer_models_lines._get_transfer_move_lines_values(*args)
        exp = [{
            'name': 'Automatic Transfer (from account MA001 with analytic account(s): ANAL00, ANAL01)',
            'account_id': self.destination_accounts[0].id,
            'date_maturity': args[1],
            'debit': sum(amounts),
        }, {
            'name': 'Automatic Transfer (entries with analytic account(s): ANAL00, ANAL01)',
            'account_id': self.origin_accounts[0].id,
            'date_maturity': args[1],
            'credit': sum(amounts),
        }]
        self.assertListEqual(exp, res,
                             'Only first transfer model line should be handled, second should get 0 and thus not be added')

    def test__get_transfer_move_lines_values(self):
        amounts = [4242.0, 1234.56]
        aaccounts = [self._create_analytic_account('ANAL0' + str(i)) for i in range(3)]
        self._create_basic_move(
            cred_account=self.destination_accounts[0].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[0],
            deb_analytic=aaccounts[0].id
        )
        self._create_basic_move(
            cred_account=self.destination_accounts[1].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[1],
            deb_analytic=aaccounts[2].id
        )
        transfer_model_line_1 = self._add_transfer_model_line(self.destination_accounts[0].id,
                                                      analytic_account_ids=[aaccounts[0].id, aaccounts[1].id])
        transfer_model_line_2 = self._add_transfer_model_line(self.destination_accounts[1].id,
                                                      analytic_account_ids=[aaccounts[2].id])

        transfer_models_lines = transfer_model_line_1 + transfer_model_line_2
        args = [fields.Date.to_date('2019-01-01'), fields.Date.to_date('2019-12-19')]
        res = transfer_models_lines._get_transfer_move_lines_values(*args)
        exp = [
            {
                'name': 'Automatic Transfer (from account MA001 with analytic account(s): ANAL00, ANAL01)',
                'account_id': self.destination_accounts[0].id,
                'date_maturity': args[1],
                'debit': amounts[0],
            },
            {
                'name': 'Automatic Transfer (entries with analytic account(s): ANAL00, ANAL01)',
                'account_id': self.origin_accounts[0].id,
                'date_maturity': args[1],
                'credit': amounts[0],
            },
            {
                'name': 'Automatic Transfer (from account MA001 with analytic account(s): ANAL02)',
                'account_id': self.destination_accounts[1].id,
                'date_maturity': args[1],
                'debit': amounts[1],
            },
            {
                'name': 'Automatic Transfer (entries with analytic account(s): ANAL02)',
                'account_id': self.origin_accounts[0].id,
                'date_maturity': args[1],
                'credit': amounts[1],
            }
        ]
        self.assertListEqual(exp, res)

    @patch('odoo.addons.account_auto_transfer.models.transfer_model.TransferModel._get_move_lines_base_domain')
    def test__get_move_lines_domain(self, patched):
        return_val = [('bla', '=', 42)]
        # we need to copy return val as there are edge effects due to mocking
        # return_value is modified by the function call)
        patched.return_value = return_val[:]
        args = [fields.Date.to_date('2019-01-01'), fields.Date.to_date('2019-12-19')]
        aaccount_1 = self._create_analytic_account('ANAL01')
        aaccount_2 = self._create_analytic_account('ANAL02')
        percent = 42.42
        analytic_transfer_model_line = self._add_transfer_model_line(self.destination_accounts[0].id,
                                                             analytic_account_ids=[aaccount_1.id, aaccount_2.id])
        percent_transfer_model_line = self._add_transfer_model_line(self.destination_accounts[1].id, percent=percent)

        anal_res = analytic_transfer_model_line._get_move_lines_domain(*args)
        anal_expected = return_val
        patched.assert_called_once_with(*args)
        self.assertListEqual(anal_res, anal_expected)
        patched.reset_mock()

        perc_res = percent_transfer_model_line._get_move_lines_domain(*args)
        patched.assert_called_once_with(*args)
        self.assertListEqual(perc_res, patched.return_value)

    def test__get_origin_account_transfer_move_line_values(self):
        percent = 92.42
        transfer_model_line = self._add_transfer_model_line(self.destination_accounts[0].id, percent=percent)
        origin_account = self.origin_accounts[0]
        amount = 4200.42
        is_debit = True
        write_date = fields.Date.to_date('2019-12-19')
        params = [origin_account, amount, is_debit, write_date]
        result = transfer_model_line._get_origin_account_transfer_move_line_values(*params)
        expected = {
            'name': 'Automatic Transfer (to account %s)' % self.destination_accounts[0].code,
            'account_id': origin_account.id,
            'date_maturity': write_date,
            'credit' if is_debit else 'debit': amount
        }
        self.assertDictEqual(result, expected)

    def test__get_destination_account_transfer_move_line_values(self):
        aaccount_1 = self._create_analytic_account('ANAL01')
        aaccount_2 = self._create_analytic_account('ANAL02')
        percent = 42.42
        analytic_transfer_model_line = self._add_transfer_model_line(self.destination_accounts[0].id,
                                                             analytic_account_ids=[aaccount_1.id, aaccount_2.id])
        percent_transfer_model_line = self._add_transfer_model_line(self.destination_accounts[1].id, percent=percent)
        origin_account = self.origin_accounts[0]
        amount = 4200
        is_debit = True
        write_date = fields.Date.to_date('2019-12-19')
        params = [origin_account, amount, is_debit, write_date]
        anal_result = analytic_transfer_model_line._get_destination_account_transfer_move_line_values(*params)
        aaccount_names = ', '.join([aac.name for aac in [aaccount_1, aaccount_2]])
        anal_expected_result = {
            'name': 'Automatic Transfer (from account %s with analytic account(s): %s)' % (
                origin_account.code, aaccount_names),
            'account_id': self.destination_accounts[0].id,
            'date_maturity': write_date,
            'debit' if is_debit else 'credit': amount
        }
        self.assertDictEqual(anal_result, anal_expected_result)
        percent_result = percent_transfer_model_line._get_destination_account_transfer_move_line_values(*params)
        percent_expected_result = {
            'name': 'Automatic Transfer (%s%% from account %s)' % (percent, self.origin_accounts[0].code),
            'account_id': self.destination_accounts[1].id,
            'date_maturity': write_date,
            'debit' if is_debit else 'credit': amount
        }
        self.assertDictEqual(percent_result, percent_expected_result)

    def test__get_transfer_move_lines_values_same_partner_ids(self):
        """
        Make sure we only process the account moves once.
        Here the second line references a partner already handled in the first one.
        The second transfer should thus not be apply on the account lines already handled by the first transfer.
        """
        amounts = [4242.42, 1234.56]
        partner_ids = [self._create_partner('partner' + str(i))for i in range(2)]
        self._create_basic_move(
            cred_account=self.destination_accounts[0].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[0],
            partner_id=partner_ids[0].id,
            date_str='2019-02-01'
        )
        self._create_basic_move(
            cred_account=self.destination_accounts[1].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[1],
            partner_id=partner_ids[1].id,
            date_str='2019-02-01'
        )
        self._create_basic_move(
            cred_account=self.destination_accounts[0].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[0],
            date_str='2019-02-01'
        )
        transfer_model_line_1 = self._add_transfer_model_line(self.destination_accounts[0].id,
                                                      partner_ids=[partner_ids[0].id, partner_ids[1].id])
        transfer_model_line_2 = self._add_transfer_model_line(self.destination_accounts[1].id,
                                                      partner_ids=[partner_ids[0].id])

        transfer_models_lines = transfer_model_line_1 + transfer_model_line_2
        args = [fields.Date.to_date('2019-01-01'), fields.Date.to_date('2019-12-19')]
        res = transfer_models_lines._get_transfer_move_lines_values(*args)
        exp = [{
            'name': 'Automatic Transfer (from account MA001 with partner(s): partner0, partner1)',
            'account_id': self.destination_accounts[0].id,
            'date_maturity': args[1],
            'debit': sum(amounts),
        }, {
            'name': 'Automatic Transfer (entries with partner(s): partner0, partner1)',
            'account_id': self.origin_accounts[0].id,
            'date_maturity': args[1],
            'credit': sum(amounts),
        }]
        self.assertListEqual(exp, res,
                             'Only first transfer model line should be handled, second should get 0 and thus not be added')

    def test__get_transfer_move_lines_values_partner(self):
        """
        Create account moves and transfer, verify that the result of the auto transfer is correct.
        """
        amounts = [4242.0, 1234.56]
        aaccounts = [self._create_analytic_account('ANAL00')]
        partner_ids = [self._create_partner('partner' + str(i))for i in range(2)]
        self._create_basic_move(
            cred_account=self.destination_accounts[2].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[0],
            partner_id=partner_ids[0].id,
            date_str='2019-02-01'
        )
        self._create_basic_move(
            cred_account=self.destination_accounts[3].id,
            deb_account=self.origin_accounts[0].id,
            amount=amounts[1],
            deb_analytic=aaccounts[0].id,
            partner_id=partner_ids[1].id,
            date_str='2019-02-01'
        )
        transfer_model_line_1 = self._add_transfer_model_line(self.destination_accounts[3].id,
                                                      analytic_account_ids=[aaccounts[0].id],
                                                      partner_ids=[partner_ids[1].id])
        transfer_model_line_2 = self._add_transfer_model_line(self.destination_accounts[2].id,
                                                      partner_ids=[partner_ids[0].id])

        transfer_models_lines = transfer_model_line_1 + transfer_model_line_2
        args = [fields.Date.to_date('2019-01-01'), fields.Date.to_date('2019-12-19')]
        res = transfer_models_lines._get_transfer_move_lines_values(*args)
        exp = [
            {
                'name': 'Automatic Transfer (from account MA001 with analytic account(s): ANAL00 and partner(s): partner1)',
                'account_id': self.destination_accounts[3].id,
                'date_maturity': args[1],
                'debit': amounts[1],
            },
            {
                'name': 'Automatic Transfer (entries with analytic account(s): ANAL00 and partner(s): partner1)',
                'account_id': self.origin_accounts[0].id,
                'date_maturity': args[1],
                'credit': amounts[1],
            },
            {
                'name': 'Automatic Transfer (from account MA001 with partner(s): partner0)',
                'account_id': self.destination_accounts[2].id,
                'date_maturity': args[1],
                'debit': amounts[0],
            },
            {
                'name': 'Automatic Transfer (entries with partner(s): partner0)',
                'account_id': self.origin_accounts[0].id,
                'date_maturity': args[1],
                'credit': amounts[0],
            },
        ]
        self.assertListEqual(exp, res)
