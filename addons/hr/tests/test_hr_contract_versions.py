# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from psycopg2.errors import CheckViolation

from odoo.tests import tagged
from odoo.tests.common import TransactionCase, freeze_time
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

@tagged('post_install', '-at_install')
class TestHrContractVersions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
            'country_id': cls.env.ref('base.us').id,
        })
        cls.env.user.company_id = cls.company
        cls.employee = cls.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2025-01-01'
        })

    def create_contract_with_versions(self, date_start, date_end, base_version, other_versions_to_create=[]):
        base_version.update({
            'contract_date_start': date_start,
            'contract_date_end': date_end,
        })
        other_versions_in_contract = self.env['hr.version']
        for date_version in other_versions_to_create:
            version = self.employee.create_version({ 'date_version': date_version })
            if version.contract_date_start:
                other_versions_in_contract |= version
        return base_version | other_versions_in_contract

    def assert_contract_versions(self, date_start, date_end, number_of_contract_expected, versions_per_contract_expected):
        versions_per_contract = self.employee._get_contract_versions(date_start, date_end)[self.employee.id]
        self.assertEqual(len(versions_per_contract), number_of_contract_expected, "%s contract should be found" % number_of_contract_expected)
        for vpc, vpc_e in zip(versions_per_contract, versions_per_contract_expected):
            self.assertEqual(vpc, vpc_e, "invalid number of versions (%s instead of %s) for this contract : contract_date_start : %s" % (len(vpc), len(vpc_e), vpc_e[0].contract_date_start))

    def assert_contract(self, date_start, date_end, use_latest_version, contract_expected):
        contracts = self.employee._get_contracts(date_start, date_end, use_latest_version)[self.employee.id]
        for c, c_e in zip(contracts, contract_expected):
            self.assertEqual(c, c_e, "invalid contracts")

    # tests _get_contract_versions()
    """ Timeline for this setup and tests
        V  : versions
        C  : first version of the contract
        =  : contract
        
        1/
                     04/01               7/31
        2025|C---------=====================----------|
           01/01               06/01                12/01 
        
        2/
                     04/01               7/31
        2025|----------==========C==========----------|
           01/01               06/01                12/01 
        
        3/
                     04/01               7/31
        2025|----------=====================---------C|
           01/01               06/01                12/01 
    """
    def setup_1contract_1version(self):
        expected_versions_contract = self.create_contract_with_versions(
            "2025-04-01",
            "2025-07-31",
            self.employee.version_id,
        )
        return dict(
            expected_versions_contract=expected_versions_contract
        )

    def test_1contract_1version(self):
        """
        We should retrieve the contract
        """
        res = self.setup_1contract_1version()
        date_versions = ['2025-01-01', '2025-06-01', '2025-12-31']
        for date_version in date_versions:
            self.employee.date_version = date_version
            self.assert_contract_versions(
                None,
                None,
                1,
                [res["expected_versions_contract"]]
            )
            self.assert_contract(
                None,
                None,
                True,
                res["expected_versions_contract"][-1]
            )
            self.assert_contract(
                None,
                None,
                False,
                res["expected_versions_contract"][-1]
            )

    def test_1contract_1version_w_date_start(self):
        """
        We should retrieve the contract
        """
        res = self.setup_1contract_1version()
        date_versions = ['2025-01-01', '2025-06-01', '2025-12-31']
        for date_version in date_versions:
            self.employee.date_version = date_version
            self.assert_contract_versions(
                date(2025, 3, 1),
                None,
                1,
                [res["expected_versions_contract"]]
            )
            self.assert_contract(
                date(2025, 3, 1),
                None,
                True,
                res["expected_versions_contract"][-1]
            )
            self.assert_contract(
                date(2025, 3, 1),
                None,
                False,
                res["expected_versions_contract"][0]
            )

    def test_1contract_1version_w_date_start_date_end(self):
        """
        We should retrieve the contract
        """
        res = self.setup_1contract_1version()
        date_versions = ['2025-01-01', '2025-06-01', '2025-12-31']
        for date_version in date_versions:
            self.employee.date_version = date_version
            self.assert_contract_versions(
                date(2025, 5, 15),
                date(2025, 6, 15),
                1,
                [res["expected_versions_contract"]]
            )
            self.assert_contract(
                date(2025, 5, 15),
                date(2025, 6, 15),
                True,
                res["expected_versions_contract"][-1]
            )
            self.assert_contract(
                date(2025, 5, 15),
                date(2025, 6, 15),
                False,
                res["expected_versions_contract"][0]
            )

    def test_1contract_1version_w_date_end(self):
        """
        We should retrieve the contract
        """
        res = self.setup_1contract_1version()
        date_versions = ['2025-01-01', '2025-06-01', '2025-12-31']
        for date_version in date_versions:
            self.employee.date_version = date_version
            self.assert_contract_versions(
                None,
                date(2025, 8, 31),
                1,
                [res["expected_versions_contract"]]
            )
            self.assert_contract(
                None,
                date(2025, 8, 31),
                True,
                res["expected_versions_contract"][-1]
            )
            self.assert_contract(
                None,
                date(2025, 8, 31),
                False,
                res["expected_versions_contract"][0]
            )

    """ Timeline for this setup
        V  : versions
        C  : first version of the contract
        =  : contract
        
                     04/01=========================07/31
        2025|C---------V---------------V------V--------VV---------|
           01/01     04/01           06/01  07/01  07/31;08/01 
    """
    def setup_1contract_3version(self):
        expected_versions_contract = self.create_contract_with_versions(
            "2025-04-01",
            "2025-07-31",
            self.employee.version_id,
            [
                "2025-04-01",
                "2025-06-01",
                "2025-07-01",
                "2025-07-31",
            ]
        )
        versions_not_in_contract = self.employee.create_version({ 'date_version': '2025-08-01' })
        return dict(
            expected_versions_contract=expected_versions_contract,
            versions_not_in_contract=versions_not_in_contract
        )


    def test_1contract_3version(self):
        """
        Without a date limit, we should retrieve all contracts
        """
        res = self.setup_1contract_3version()
        self.assert_contract_versions(
            None,
            None,
            1,
            [res["expected_versions_contract"]]
        )
        self.assert_contract(
            None,
            None,
            True,
            res["expected_versions_contract"][-1]
        )
        self.assert_contract(
            None,
            None,
            False,
            res["expected_versions_contract"][0]
        )

    def test_1contract_3version_w_date_start(self):
        """
        With only this start date limit (2025-3-1), we should retrieve all contracts
        """
        res = self.setup_1contract_3version()
        self.assert_contract_versions(
            date(2025, 3, 1),
            None,
            1,
            [res["expected_versions_contract"]]
        )
        self.assert_contract(
            date(2025, 3, 1),
            None,
            True,
            res["expected_versions_contract"][-1]
        )
        self.assert_contract(
            date(2025, 3, 1),
            None,
            False,
            res["expected_versions_contract"][0]
        )

    def test_1contract_3version_w_date_start_date_end(self):
        """
        With this date range (2025-5-15;2025-6-15), no contracts should be retrieved (even if versions are in the range)
        """
        res = self.setup_1contract_3version()
        self.assert_contract_versions(
            date(2025, 5, 15),
            date(2025, 6, 15),
            1,
            [res["expected_versions_contract"]]
        )
        self.assert_contract(
            date(2025, 4, 15),
            date(2025, 6, 15),
            True,
            res["expected_versions_contract"][2]
        )
        self.assert_contract(
            date(2025, 4, 15),
            date(2025, 6, 15),
            False,
            res["expected_versions_contract"][1]
        )
        self.assert_contract(
            date(2025, 6, 15),
            date(2025, 7, 15),
            True,
            res["expected_versions_contract"][3]
        )
        self.assert_contract(
            date(2025, 6, 15),
            date(2025, 8, 15),
            False,
            res["expected_versions_contract"][2]
        )

    def test_1contract_3version_w_date_end(self):
        """
        With only this end date limit (2025-8-31), we should retrieve the first contract only
        """
        res = self.setup_1contract_3version()
        self.assert_contract_versions(
            None,
            date(2025, 8, 31),
            1,
            [res["expected_versions_contract"]]
        )
        self.assert_contract(
            None,
            date(2025, 8, 31),
            True,
            res["expected_versions_contract"][-1]
        )
        self.assert_contract(
            None,
            date(2025, 8, 31),
            False,
            res["expected_versions_contract"][0]
        )

    """ Timeline for this setup
        V  : versions
        C  : first version of the contract
        =  : contract
        
                      4/01              5/15 6/15              7/31
        2025|C---------====================-C-====================----------|
           01/01                          06/01 
    """
    def setup_2contract_1version(self):
        expected_versions_contract1 = self.create_contract_with_versions(
            "2025-04-01",
            "2025-05-15",
            self.employee.version_id,
        )
        expected_versions_contract2 = self.create_contract_with_versions(
            "2025-06-15",
            "2025-07-31",
            self.employee.create_version({'date_version': '2025-06-01'}),
        )
        return dict(
            expected_versions_contract1=expected_versions_contract1,
            expected_versions_contract2=expected_versions_contract2
        )

    def test_2contract_1version(self):
        """
        Without a date limit, we should retrieve all contracts
        """
        res = self.setup_2contract_1version()
        self.assert_contract_versions(
            None,
            None,
            2,
            [
                res["expected_versions_contract1"],
                res["expected_versions_contract2"]
            ])
        self.assert_contract(
            None,
            None,
            True,
            res["expected_versions_contract1"][-1] | res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            None,
            None,
            False,
            res["expected_versions_contract1"][0] | res["expected_versions_contract2"][0]
        )

    def test_2contract_1version_w_date_start(self):
        """
        With only this start date limit (2025-3-1), we should retrieve all contracts
        """
        res = self.setup_2contract_1version()
        self.assert_contract_versions(
            date(2025, 3, 1),
            None,
            2,
            [
                res["expected_versions_contract1"],
                res["expected_versions_contract2"]
            ])
        self.assert_contract(
            date(2025, 3, 1),
            None,
            True,
            res["expected_versions_contract1"][-1] | res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            date(2025, 3, 1),
            None,
            False,
            res["expected_versions_contract1"][0] | res["expected_versions_contract2"][0]
        )

    def test_2contract_1version_w_date_start_date_end(self):
        """
        With this date range (2025-5-15;2025-6-15), no contracts should be retrieved (even if versions are in the range)
        """
        res = self.setup_2contract_1version()
        self.assert_contract_versions(
            date(2025, 5, 15),
            date(2025, 6, 15),
            0,
            []
        )
        self.assert_contract(
            date(2025, 4, 15),
            date(2025, 6, 15),
            True,
            res["expected_versions_contract1"][-1]
        )
        self.assert_contract(
            date(2025, 4, 15),
            date(2025, 6, 15),
            False,
            res["expected_versions_contract1"][0]
        )
        self.assert_contract(
            date(2025, 6, 15),
            date(2025, 7, 15),
            True,
            res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            date(2025, 6, 15),
            date(2025, 7, 15),
            False,
            res["expected_versions_contract2"][0]
        )

    def test_2contract_1version_w_date_end(self):
        """
        With only this end date limit (2025-8-31), we should retrieve the first contract only
        """
        res = self.setup_2contract_1version()
        self.assert_contract_versions(
            None,
            date(2025, 8, 31),
            2,
            [
                res["expected_versions_contract1"],
                res["expected_versions_contract2"]
            ])
        self.assert_contract(
            None,
            date(2025, 8, 31),
            True,
            res["expected_versions_contract1"][-1] | res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            None,
            date(2025, 8, 31),
            False,
            res["expected_versions_contract1"][0] | res["expected_versions_contract2"][0]
        )

    def test_2contract_1version_w_other_date_end(self):
        """
        With only this end date limit (2025-6-15), we should retrieve the first contract only
        """
        res = self.setup_2contract_1version()
        self.assert_contract_versions(
            None,
            date(2025, 6, 15),
            1,
            [
                res["expected_versions_contract1"]
            ]
        )

    """ Timeline for this setup
        V  : versions
        C  : first version of the contract
        =  : contract
        
                       4/01============5/15               6/15============7/31
        2025|C---------V------------------VV------C-------V------------------VV---------|
            1/1       4/1              5/15;5/16 6/1      6/15            7/31;8/1
    """
    def setup_2contract_3version(self):
        expected_versions_contract1 = self.create_contract_with_versions(
            "2025-04-01",
            "2025-05-15",
            self.employee.version_id,
            [
                "2025-04-01",
                "2025-05-15",
            ]
        )
        versions_not_in_contract = self.employee.create_version({ 'date_version': '2025-05-16' })
        expected_versions_contract2 = self.create_contract_with_versions(
            "2025-06-15",
            "2025-07-31",
            self.employee.create_version({'date_version': '2025-06-01'}),
            [
                "2025-06-15",
                "2025-07-31",
            ]
        )
        versions_not_in_contract |= self.employee.create_version({ 'date_version': '2025-08-01' })
        return dict(
            expected_versions_contract1=expected_versions_contract1,
            expected_versions_contract2=expected_versions_contract2,
            versions_not_in_contract=versions_not_in_contract
        )

    def test_2contract_3version(self):
        """
        Without a date limit, we should retrieve all contracts
        """
        res = self.setup_2contract_3version()
        self.assert_contract_versions(
            None,
            None,
            2,
            [
                res["expected_versions_contract1"],
                res["expected_versions_contract2"]
            ]
        )
        self.assert_contract(
            None,
            None,
            True,
            res["expected_versions_contract1"][-1] | res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            None,
            None,
            False,
            res["expected_versions_contract1"][0] | res["expected_versions_contract2"][0]
        )

    def test_2contract_3version_w_date_start(self):
        """
        With only this start date limit (2025-3-1), we should retrieve all contracts
        """
        res = self.setup_2contract_3version()
        self.assert_contract_versions(
            date(2025, 3, 1),
            None,
            2,
            [
                res["expected_versions_contract1"],
                res["expected_versions_contract2"]
            ]
        )
        self.assert_contract(
            date(2025, 3, 1),
            None,
            True,
            res["expected_versions_contract1"][-1] | res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            date(2025, 3, 1),
            None,
            False,
            res["expected_versions_contract1"][0] | res["expected_versions_contract2"][0]
        )


    def test_2contract_3version_w_date_start_date_end(self):
        """
        With this date range (2025-5-15;2025-6-15), no contracts should be retrieved (even if versions are in the range)
        """
        res = self.setup_2contract_3version()
        self.assert_contract_versions(
            date(2025, 5, 15),
            date(2025, 6, 15),
            0,
            []
        )
        self.assert_contract(
            date(2025, 4, 15),
            date(2025, 6, 15),
            True,
            res["expected_versions_contract1"][-1]
        )
        self.assert_contract(
            date(2025, 4, 15),
            date(2025, 6, 15),
            False,
            res["expected_versions_contract1"][1]
        )
        self.assert_contract(
            date(2025, 6, 15),
            date(2025, 7, 15),
            True,
            res["expected_versions_contract2"][1]
        )
        self.assert_contract(
            date(2025, 6, 15),
            date(2025, 7, 15),
            False,
            res["expected_versions_contract2"][1]
        )


    def test_2contract_3version_w_date_end(self):
        """
        With only this end date limit (2025-8-31), we should retrieve all contracts
        """
        res = self.setup_2contract_3version()
        self.assert_contract_versions(
            None,
            date(2025, 8, 31),
            2,
            [
                res["expected_versions_contract1"],
                res["expected_versions_contract2"]
            ]
        )
        self.assert_contract(
            None,
            date(2025, 8, 31),
            True,
            res["expected_versions_contract1"][-1] | res["expected_versions_contract2"][-1]
        )
        self.assert_contract(
            None,
            date(2025, 8, 31),
            False,
            res["expected_versions_contract1"][0] | res["expected_versions_contract2"][0]
        )

    def test_2contract_3version_w_other_date_end(self):
        """
        With only this end date limit (2025-6-15), we should retrieve the first contract only
        """
        res = self.setup_2contract_3version()
        self.assert_contract_versions(
            None,
            date(2025, 6, 15),
            1,
            [
                res["expected_versions_contract1"]
            ]
        )

