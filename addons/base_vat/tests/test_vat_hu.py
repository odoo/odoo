# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("-standard", "external")
class TestVatHu(TransactionCase):
    def test_validate_vat(self):
        valid_codes = [
            "HU27725414",
            "27725414-2-13",
            "27725414213",
            "8071592153",
        ]

        invalid_codes = [
            "HU27725410",
            "HU2772541",
            "HU277254140",
            "27725410-2-13",
            "27725414-2-1",
            "27725414-2-133",
            "27725414-21-3",
            "2772541421-3",
            "2772541-42-13",
            "27725410213",
            "2772541421",
            "277254142133",
        ]

        partners = self.env["res.partner"]
        hu_country = self.env.ref("base.hu")

        for i, code in enumerate(invalid_codes):
            with self.assertRaises(UserError):
                partners += self.env["res.partner"].create(
                    {
                        "name": f"partner_{i}",
                        "vat": code,
                        "country_id": hu_country.id,
                    }
                )

        for i, code in enumerate(valid_codes):
            partners += self.env["res.partner"].create(
                {
                    "name": f"partner_{i}",
                    "vat": code,
                    "country_id": hu_country.id,
                }
            )

        self.assertEqual(len(partners), len(valid_codes), "Hungarian VAT validation check failed")
