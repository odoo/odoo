# Copyright (c) 2018 Daniel Campos <danielcampos@avanzosc.es> - Avanzosc S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from .common import CommonCase


class TestProductBrand(CommonCase):
    def test_products_count(self):
        self.assertEqual(
            self.product_brand.products_count, 0, "Error product count does not match"
        )
        self.product.product_brand_id = self.product_brand.id
        self.assertEqual(
            self.product_brand.products_count, 1, "Error product count does not match"
        )
