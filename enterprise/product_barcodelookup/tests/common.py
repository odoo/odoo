from contextlib import contextmanager
from unittest.mock import patch
from ..models.product_template import ProductTemplate
from odoo.tests import common


class MockAPIBarcodelookup(common.BaseCase):
    @contextmanager
    def mockBarcodelookupAutofill(self, default_data=None):
        def barcode_lookup(barcode):
            mock_product_data = {
                "products": [
                    {
                        "title": "Odoo Scale up",
                        "category": "Test Category > Business & Industrial",
                        "manufacturer": "Odoo S.a",
                        "brand": "Odoo",
                        "color": "Purple",
                        "gender": "Test Gender",
                        "material": "cotton",
                        "size": "9.75 × 8.25 in",
                        "description": "Test Description",
                        "length": "190 cm",
                        "width": "130 cm",
                        "height": "300 cm",
                        "weight": "1.5 kg",
                        "images": [],
                        "features": [
                            "Test features",
                        ],
                        "stores": [
                            {
                                "name": "Novatech Ltd",
                                "country": "USA",
                                "currency": "USD",
                                "currency_symbol": "$",
                                "price": "115.00",
                                "tax": [],
                                "availability": "in stock",
                                "last_update": "2024-04-18 06:14:04"
                            },
                        ]
                    }
                ]
            }
            return mock_product_data

        try:
            with patch.object(ProductTemplate, 'barcode_lookup', side_effect=barcode_lookup):
                yield
        finally:
            pass
