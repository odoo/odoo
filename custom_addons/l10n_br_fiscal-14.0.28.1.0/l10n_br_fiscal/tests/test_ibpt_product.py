# Copyright 2019 Akretion - Renato Lima <renato.lima@akretion.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from .test_ibpt import TestIbpt, mocked_requests_get, not_every_day_test


class TestIbptProduct(TestIbpt):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ncm_85030010 = cls.env.ref("l10n_br_fiscal.ncm_85030010")
        cls.ncm_85014029 = cls.env.ref("l10n_br_fiscal.ncm_85014029")

        cls.product_tmpl_1 = cls._create_product_tmpl(
            name="Product Test 1 - With NCM: 8503.00.10", ncm=cls.ncm_85030010
        )

        cls.product_tmpl_2 = cls._create_product_tmpl(
            name="Product Test 2 - With NCM: 8503.00.10", ncm=cls.ncm_85030010
        )

        cls.product_tmpl_3 = cls._create_product_tmpl(
            name="Product Test 3 - With NCM: 8501.40.29", ncm=cls.ncm_85014029
        )

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_mock(self, mock_get):
        api_status = self.env.company.ibpt_api
        self.env.company.ibpt_api = True  # force to run the mocked query
        self.ncm_85030010.action_ibpt_inquiry()
        ncms = self.ncm_model.search(
            [("id", "in", (self.ncm_85030010.id, self.ncm_85014029.id))]
        )
        ncms._scheduled_update()
        self.env.company.ibpt_api = api_status

    @not_every_day_test
    def test_update_ibpt_product(self):
        """Check tax estimate update"""

        if not self.company.ibpt_api:
            return

        self.ncm_85030010.action_ibpt_inquiry()
        self.assertTrue(self.ncm_85030010.tax_estimate_ids)

        self.ncm_85014029.action_ibpt_inquiry()
        self.assertTrue(self.ncm_85014029.tax_estimate_ids)

        self.tax_estimate_model.search(
            [("ncm_id", "in", (self.ncm_85030010.id, self.ncm_85014029.id))]
        ).unlink()

    @not_every_day_test
    def test_ncm_count_product_template(self):
        """Check product template relation with NCM"""

        if not self.company.ibpt_api:
            return

        self.assertEqual(self.ncm_85030010.product_tmpl_qty, 2)
        self.assertEqual(self.ncm_85014029.product_tmpl_qty, 1)

    @not_every_day_test
    def test_update_scheduled(self):
        """Check NCM update scheduled"""

        if not self.company.ibpt_api:
            return

        ncms = self.ncm_model.search(
            [("id", "in", (self.ncm_85030010.id, self.ncm_85014029.id))]
        )
        ncms._scheduled_update()

        self.assertTrue(self.ncm_85030010.tax_estimate_ids)
        self.assertTrue(self.ncm_85014029.tax_estimate_ids)

        self.tax_estimate_model.search(
            [("ncm_id", "in", (self.ncm_85030010.id, self.ncm_85014029.id))]
        ).unlink()
