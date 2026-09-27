# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon


@tagged('post_install', '-at_install')
class TestHrVersionContractOverlap(TestHrCommon):
    """
    Versions sharing the same contract_date_start, contract_date_end are
    successive states of one contract, delimited by their date_version. The
    method must return only the version(s) effective during the period.
    """

    def assert_versions(self, date_from, date_to, expected):
        result = self.employee._get_versions_with_contract_overlap_with_period(date_from, date_to)
        self.assertEqual(result, expected, "period [%s, %s]" % (date_from, date_to))

    def add_version(self, date_version, start, end=False):
        version = self.employee.create_version({'date_version': date_version})
        version.write({'contract_date_start': start, 'contract_date_end': end})
        return version

    def test_no_contract(self):
        self.assert_versions(date(2026, 1, 1), date(2026, 12, 31), self.env['hr.version'])

    def test_single_version_covers_whole_contract(self):
        # single version effective on 03-01 but contract starts 01-01: it must
        # cover the whole contract, before and after its date_version.
        version = self.employee.version_id
        version.write({
            'date_version': date(2026, 3, 1),
            'contract_date_start': date(2026, 1, 1),
            'contract_date_end': date(2026, 6, 30),
        })
        self.assert_versions(date(2025, 12, 1), date(2025, 12, 31), self.env['hr.version'])
        self.assert_versions(date(2026, 1, 1), date(2026, 1, 31), version)
        self.assert_versions(date(2026, 4, 1), date(2026, 4, 30), version)
        self.assert_versions(date(2026, 7, 1), date(2026, 7, 31), self.env['hr.version'])

    def test_two_versions_same_contract(self):
        # an amendment effective 03-01 on the same contract.
        v1 = self.employee.version_id
        v1.write({'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
        v2 = self.add_version(date(2026, 3, 1), date(2026, 1, 1))
        self.assert_versions(date(2026, 2, 1), date(2026, 2, 28), v1)
        self.assert_versions(date(2026, 4, 1), date(2026, 4, 30), v2)
        self.assert_versions(date(2026, 2, 15), date(2026, 3, 15), v1 | v2)

    def test_first_version_anchored_to_contract_start(self):
        # both date_versions are after contract_date_start, the earliest still covers the head of the contract.
        v1 = self.employee.version_id
        v1.write({'date_version': date(2026, 2, 1), 'contract_date_start': date(2026, 1, 1)})
        v2 = self.add_version(date(2026, 3, 1), date(2026, 1, 1))
        self.assert_versions(date(2026, 1, 1), date(2026, 1, 31), v1)
        self.assert_versions(date(2026, 4, 1), date(2026, 4, 30), v2)

    def test_two_contracts_not_collapsed(self):
        v1 = self.employee.version_id
        v1.write({'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
                  'contract_date_end': date(2026, 3, 31)})
        v2 = self.add_version(date(2026, 4, 1), date(2026, 4, 1))
        self.assert_versions(date(2026, 1, 1), date(2026, 1, 31), v1)
        self.assert_versions(date(2026, 4, 1), date(2026, 4, 30), v2)
        self.assert_versions(date(2026, 1, 1), date(2026, 4, 30), v1 | v2)
