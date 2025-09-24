# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestHrContractVersions(TransactionCase):
    """
    TestHrContractVersions is responsible for testing the behavior and validity of versions
    with contracts.

    This class tests 2 helper methods: `_get_contract_versions()` and `_get_contracts()`
    There are multiple scenarios:
        - No contract, 1 version
        - 1 contract with 1 version
        - 1 contract with 5 versions
        - 2 contracts with 1 version each
        - 2 contracts with 3 versions each

    For each of them, multiple tests are performed with different start_date, end_date and use_latest_version
    """

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

    def create_version(self, date_version):
        return self.employee.create_version({
            'date_version': date_version,
        })

    def create_versions(self, *dates):
        res = self.env["hr.version"]
        for date_version in dates:
            res |= self.create_version(date_version)
        return res

    def assert_get_contract_versions(self, date_start, date_end, versions_per_contract_expected):
        versions_per_contract = self.employee._get_contract_versions(date_start, date_end)[self.employee.id]
        self.assertEqual(len(versions_per_contract), len(versions_per_contract_expected), "%s contract should be found" % len(versions_per_contract_expected))
        for vpc, vpc_e in zip(versions_per_contract.values(), versions_per_contract_expected):
            self.assertEqual(vpc, vpc_e, "invalid number of versions (%s instead of %s) for this contract : contract_date_start : %s" % (len(vpc), len(vpc_e), vpc_e[0].contract_date_start))

    def assert_get_contracts(self, date_start, date_end, use_latest_version, contracts_expected):
        contracts = self.employee._get_contracts(date_start, date_end, use_latest_version)[self.employee.id]
        for c, c_e in zip(contracts, contracts_expected):
            self.assertEqual(c, c_e, "invalid contracts")

    def test_0contract_1version(self):
        """
        We should retrieve no versions, because no contract is defined
        """
        for date_version in ['2025-01-01', '2025-06-01', '2025-12-31']:
            self.employee.date_version = date_version
            for date_start in (None, date(2025, 3, 1)):
                for date_end in (None, date(2025, 6, 15)):
                    for use_latest_version in (True, False):
                        self.assert_get_contract_versions(
                            date_start,
                            date_end,
                            []
                        )
                        self.assert_get_contracts(
                            date_start,
                            date_end,
                            use_latest_version,
                            []
                        )

    """ Timeline for this test
        V  : versions
        C  : first version of the contract
        =  : contract

        1/
                     04/01               7/31
        2025|C---------=====================----------|
           01/01               06/01                12/31

        2/
                     04/01               7/31
        2025|----------==========C==========----------|
           01/01               06/01                12/31

        3/
                     04/01               7/31
        2025|----------=====================---------C|
           01/01               06/01                12/31
    """
    def test_1contract_1version(self):
        """
        We should always retrieve the only existing version
        """
        unique_version = self.employee.version_id
        unique_version.contract_date_start = date(2025, 4, 1)
        unique_version.contract_date_end = date(2025, 7, 31)
        for date_version in ['2025-01-01', '2025-06-01', '2025-12-31']:
            unique_version.date_version = date_version
            for date_start in (None, date(2025, 3, 1), date(2025, 4, 1)):
                for date_end in (None, date(2025, 4, 1), date(2025, 6, 15), date(2025, 7, 31)):
                    for use_latest_version in (True, False):
                        self.assert_get_contract_versions(
                            date_start,
                            date_end,
                            [unique_version]
                        )
                        self.assert_get_contracts(
                            date_start,
                            date_end,
                            use_latest_version,
                            unique_version
                        )

    """ Timeline for this setup
        V  : versions
        C  : first version of the contract
        =  : contract

                     04/01=========================07/31
        2025|C---------V---------------V------V--------VV---------|
           01/01     04/01           06/01  07/01  07/31;08/01
    """
    def setup_1contract_5version(self):
        contract_versions = self.employee.version_id | self.create_versions(
            date(2025, 4, 1),
            date(2025, 6, 1),
            date(2025, 7, 1),
            date(2025, 7, 31)
        )
        contract_versions.contract_date_start = date(2025, 4, 1)
        contract_versions.contract_date_end = date(2025, 7, 31)
        versions_not_in_contract = self.create_version(date(2025, 8, 1))
        return contract_versions, versions_not_in_contract

    def test_1contract_5version(self):
        # All versions of the contract should be retrieved
        expected_contract_versions, _ = self.setup_1contract_5version()
        self.assert_get_contract_versions(
            None,
            None,
            [expected_contract_versions]
        )
        # The last version of the contract should be retrieved
        self.assert_get_contracts(
            None,
            None,
            True,
            expected_contract_versions[-1]
        )
        # The first version of the contract should be retrieved
        self.assert_get_contracts(
            None,
            None,
            False,
            expected_contract_versions[0]
        )

    def test_1contract_5version_w_date_start(self):
        # All versions of the contract should be retrieved
        expected_contract_versions, _ = self.setup_1contract_5version()
        self.assert_get_contract_versions(
            date(2025, 3, 1),
            None,
            [expected_contract_versions]
        )
        # The last version of the contract should be retrieved
        self.assert_get_contracts(
            date(2025, 3, 1),
            None,
            True,
            expected_contract_versions[-1]
        )
        # We need to retrieve the version closest and before the start date. (first version of the contract)
        self.assert_get_contracts(
            date(2025, 3, 1),
            None,
            False,
            expected_contract_versions[0]
        )
        # We need to retrieve the version closest and before the start date. (second version of the contract)
        self.assert_get_contracts(
            date(2025, 4, 1),
            None,
            False,
            expected_contract_versions[0]
        )

    def test_1contract_5version_w_date_start_date_end(self):
        # all versions of the contract should be retrieved (even if versions are not in the range)
        expected_contract_versions, _ = self.setup_1contract_5version()
        self.assert_get_contract_versions(
            date(2025, 5, 15),
            date(2025, 6, 15),
            [expected_contract_versions]
        )
        # We need to retrieve the version closest and before the end date.
        self.assert_get_contracts(
            date(2025, 4, 15),
            date(2025, 6, 15),
            True,
            expected_contract_versions[2]
        )
        # We need to retrieve the version closest and before the start date.
        self.assert_get_contracts(
            date(2025, 4, 15),
            date(2025, 6, 15),
            False,
            expected_contract_versions[1]
        )
        # We need to retrieve the version closest and before the end date.
        self.assert_get_contracts(
            date(2025, 6, 15),
            date(2025, 7, 15),
            True,
            expected_contract_versions[3]
        )
        # We need to retrieve the version closest and before the start date.
        self.assert_get_contracts(
            date(2025, 6, 15),
            date(2025, 8, 15),
            False,
            expected_contract_versions[2]
        )

    def test_1contract_5version_w_date_end(self):
        # All versions of the contract should be retrieved
        expected_contract_versions, _ = self.setup_1contract_5version()
        self.assert_get_contract_versions(
            None,
            date(2025, 8, 31),
            [expected_contract_versions]
        )
        # We need to retrieve the version closest and before the end date. (last version of the contract)
        self.assert_get_contracts(
            None,
            date(2025, 8, 31),
            True,
            expected_contract_versions[-1]
        )
        # We need to retrieve the version closest and before the end date. (last version of the contract)
        self.assert_get_contracts(
            None,
            date(2025, 7, 31),
            True,
            expected_contract_versions[-1]
        )
        # We need to retrieve the version closest and before the end date. (second to last version of the contract)
        self.assert_get_contracts(
            None,
            date(2025, 7, 30),
            True,
            expected_contract_versions[-2]
        )
        # The first version of the contract should be retrieved
        self.assert_get_contracts(
            None,
            date(2025, 8, 31),
            False,
            expected_contract_versions[0]
        )

    """ Timeline for this setup
        V  : versions
        C  : first version of the contract
        =  : contract

                      4/01              5/15 6/15              7/31
        2025|C---------====================-C-====================----------|
           01/01                          06/01
    """
    def setup_2contract_1version_each(self):
        contract_1_version = self.employee.version_id
        contract_1_version.contract_date_start = date(2025, 4, 1)
        contract_1_version.contract_date_end = date(2025, 5, 15)

        contract_2_version = self.create_version(date(2025, 6, 1))
        contract_2_version.contract_date_start = date(2025, 6, 15)
        contract_2_version.contract_date_end = date(2025, 7, 31)

        return contract_1_version, contract_2_version

    def test_2contract_1version_each(self):
        # all versions of all contracts
        contract_1_version, contract_2_version = self.setup_2contract_1version_each()
        self.assert_get_contract_versions(
            None,
            None,
            [contract_1_version, contract_2_version]
        )
        # the latest version of each contract
        self.assert_get_contracts(
            None,
            None,
            True,
            contract_1_version | contract_2_version
        )
        # the first version of each contract
        self.assert_get_contracts(
            None,
            None,
            False,
            contract_1_version | contract_2_version
        )

    def test_2contract_1version_each_w_date_start(self):
        # all versions of all contracts
        contract_1_version, contract_2_version = self.setup_2contract_1version_each()
        self.assert_get_contract_versions(
            date(2025, 3, 1),
            None,
            [contract_1_version, contract_2_version]
        )
        #  all versions of the second contract
        self.assert_get_contract_versions(
            date(2025, 6, 15),
            None,
            [contract_2_version]
        )
        # the latest version of each contract
        self.assert_get_contracts(
            date(2025, 3, 1),
            None,
            True,
            contract_1_version | contract_2_version
        )
        # the first before the start date, of each contract
        self.assert_get_contracts(
            date(2025, 3, 1),
            None,
            False,
            contract_1_version | contract_2_version
        )

    def test_2contract_1version_each_w_date_start_date_end(self):
        # no versions, because no contract active in the range, even if versions are in the range
        contract_1_version, contract_2_version = self.setup_2contract_1version_each()
        self.assert_get_contract_versions(
            date(2025, 5, 16),
            date(2025, 6, 14),
            []
        )
        # all versions of each contract
        self.assert_get_contract_versions(
            date(2025, 5, 15),
            date(2025, 6, 15),
            [contract_1_version, contract_2_version]
        )
        # the first version before the end date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 5, 15),
            date(2025, 6, 14),
            True,
            contract_1_version
        )
        # the first version before the start date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 5, 15),
            date(2025, 6, 14),
            False,
            contract_1_version
        )
        # the first version before the end date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 5, 16),
            date(2025, 6, 15),
            True,
            contract_2_version
        )
        # the first version before the start date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 5, 16),
            date(2025, 6, 15),
            False,
            contract_2_version
        )
        # the first version before the end date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 5, 15),
            date(2025, 6, 15),
            True,
            [contract_1_version, contract_2_version]
        )
        # the first version before the start date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 5, 15),
            date(2025, 6, 15),
            False,
            [contract_1_version, contract_2_version]
        )

    def test_2contract_1version_each_w_date_end(self):
        # all versions of all contracts
        contract_1_version, contract_2_version = self.setup_2contract_1version_each()
        self.assert_get_contract_versions(
            None,
            date(2025, 8, 31),
            [contract_1_version, contract_2_version]
        )
        # all versions of the first contract
        self.assert_get_contract_versions(
            None,
            date(2025, 6, 15),
            [contract_1_version, contract_2_version]
        )
        # all versions of the first contract
        self.assert_get_contract_versions(
            None,
            date(2025, 6, 14),
            [contract_1_version]
        )
        # the first before the end date, of each contract
        self.assert_get_contracts(
            None,
            date(2025, 8, 31),
            True,
            contract_1_version | contract_2_version
        )
        # the first version of each contract
        self.assert_get_contracts(
            None,
            date(2025, 8, 31),
            False,
            contract_1_version | contract_2_version
        )

    """ Timeline for this setup
        V  : versions
        C  : first version of the contract
        =  : contract

                       4/01============5/15               6/15============7/31
        2025|C---------V------------------VV------C-------V------------------VV---------|
            1/1       4/1              5/15;5/16 6/1      6/15            7/31;8/1
    """
    def setup_2contract_3version_each(self):
        contract_1_versions = self.employee.version_id | self.create_versions(
            date(2025, 4, 1),
            date(2025, 5, 15),
        )
        contract_1_versions.contract_date_start = date(2025, 4, 1)
        contract_1_versions.contract_date_end = date(2025, 5, 15)

        versions_not_in_contract = self.create_version(date(2025, 5, 16))

        contract_2_versions = self.create_versions(
            date(2025, 6, 1),
            date(2025, 6, 15),
            date(2025, 7, 31),
        )
        contract_2_versions.contract_date_start = date(2025, 6, 15)
        contract_2_versions.contract_date_end = date(2025, 7, 31)

        versions_not_in_contract |= self.create_version(date(2025, 8, 1))

        return contract_1_versions, contract_2_versions, versions_not_in_contract

    def test_2contract_3version_each(self):
        # all versions of all contracts
        contract_1_version, contract_2_version, _ = self.setup_2contract_3version_each()
        self.assert_get_contract_versions(
            None,
            None,
            [contract_1_version, contract_2_version]
        )
        # the latest version of each contract
        self.assert_get_contracts(
            None,
            None,
            True,
            contract_1_version[-1] | contract_2_version[-1]
        )
        # the first version of each contract
        self.assert_get_contracts(
            None,
            None,
            False,
            contract_1_version[0] | contract_2_version[0]
        )

    def test_2contract_3version_each_w_date_start(self):
        # all versions of all contracts
        contract_1_version, contract_2_version, _ = self.setup_2contract_3version_each()
        self.assert_get_contract_versions(
            date(2025, 3, 1),
            None,
            [contract_1_version, contract_2_version]
        )
        # the latest version of each contract
        self.assert_get_contracts(
            date(2025, 3, 1),
            None,
            True,
            contract_1_version[-1] | contract_2_version[-1]
        )
        # the first before the start date, of each contract
        self.assert_get_contracts(
            date(2025, 3, 1),
            None,
            False,
            contract_1_version[0] | contract_2_version[0]
        )
        # the first before the start date, of each contract
        self.assert_get_contracts(
            date(2025, 4, 1),
            None,
            False,
            contract_1_version[1] | contract_2_version[0]
        )

    def test_2contract_3version_each_w_date_start_date_end(self):
        # all versions of all contracts
        contract_1_version, contract_2_version, _ = self.setup_2contract_3version_each()
        self.assert_get_contract_versions(
            date(2025, 5, 16),
            date(2025, 6, 14),
            []
        )
        # the first before the end date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 4, 15),
            date(2025, 6, 15),
            True,
            [contract_1_version[-1], contract_2_version[1]]
        )
        # the first before the start date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 4, 15),
            date(2025, 6, 15),
            False,
            [contract_1_version[0], contract_2_version[0]]
        )
        # the first before the end date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 6, 15),
            date(2025, 7, 31),
            True,
            contract_2_version[-1]
        )
        # the first before the start date, of the contract active in the range
        self.assert_get_contracts(
            date(2025, 6, 15),
            date(2025, 7, 31),
            False,
            contract_2_version[1]
        )

    def test_2contract_3version_each_w_date_end(self):
        # all versions of all contracts
        contract_1_version, contract_2_version, _ = self.setup_2contract_3version_each()
        self.assert_get_contract_versions(
            None,
            date(2025, 8, 31),
            [contract_1_version, contract_2_version]
        )
        # the first before the end date, of each contract
        self.assert_get_contracts(
            None,
            date(2025, 8, 31),
            True,
            contract_1_version[-1] | contract_2_version[-1]
        )
        # the first before the end date, of each contract
        self.assert_get_contracts(
            None,
            date(2025, 7, 31),
            True,
            contract_1_version[-1] | contract_2_version[-1]
        )
        # the first before the end date, of each contract
        self.assert_get_contracts(
            None,
            date(2025, 7, 30),
            True,
            contract_1_version[-1] | contract_2_version[-2]
        )
        # the latest version of each contract
        self.assert_get_contracts(
            None,
            date(2025, 8, 31),
            False,
            contract_1_version[0] | contract_2_version[0]
        )
