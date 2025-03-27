# Copyright 2108-2019 Francois Poizat <francois.poizat@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCommonStockBarcodes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Active group_stock_packaging and group_production_lot for user
        group_stock_packaging = cls.env.ref("product.group_stock_packaging")
        group_production_lot = cls.env.ref("stock.group_production_lot")
        cls.env.user.groups_id = [
            (4, group_stock_packaging.id),
            (4, group_production_lot.id),
        ]
        # models
        cls.StockLocation = cls.env["stock.location"]
        cls.Product = cls.env["product.product"]
        cls.ProductPackaging = cls.env["product.packaging"]
        cls.WizScanReadPicking = cls.env["wiz.stock.barcodes.read.picking"]
        cls.StockProductionLot = cls.env["stock.lot"]
        cls.StockPicking = cls.env["stock.picking"]
        cls.StockQuant = cls.env["stock.quant"]

        cls.company = cls.env.company

        # Option groups for test
        cls.option_group = cls._create_barcode_option_group()

        # warehouse and locations
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.location_1 = cls.StockLocation.create(
            {
                "name": "Test location 1",
                "usage": "internal",
                "location_id": cls.stock_location.id,
                "barcode": "8411322222568",
            }
        )
        cls.location_2 = cls.StockLocation.create(
            {
                "name": "Test location 2",
                "usage": "internal",
                "location_id": cls.stock_location.id,
                "barcode": "8470001809032",
            }
        )

        # products
        cls.product_wo_tracking = cls.Product.create(
            {
                "name": "Product test wo lot tracking",
                "type": "product",
                "tracking": "none",
                "barcode": "8480000723208",
                "packaging_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Box 10 Units",
                            "qty": 10.0,
                            "barcode": "5099206074439",
                        },
                    )
                ],
            }
        )
        cls.product_tracking = cls.Product.create(
            {
                "name": "Product test with lot tracking",
                "type": "product",
                "tracking": "lot",
                "barcode": "8433281006850",
                "packaging_ids": [
                    (
                        0,
                        0,
                        {"name": "Box 5 Units", "qty": 5.0, "barcode": "5420008510489"},
                    )
                ],
            }
        )
        cls.lot_1 = cls.StockProductionLot.create(
            {
                "name": "8411822222568",
                "product_id": cls.product_tracking.id,
                "company_id": cls.company.id,
            }
        )
        cls.quant_lot_1 = cls.StockQuant.create(
            {
                "product_id": cls.product_tracking.id,
                "lot_id": cls.lot_1.id,
                "location_id": cls.stock_location.id,
                "quantity": 100.0,
            }
        )
        cls.wiz_scan = cls.WizScanReadPicking.create(
            {"option_group_id": cls.option_group.id, "step": 1}
        )

    @classmethod
    def _create_barcode_option_group(cls):
        return cls.env["stock.barcodes.option.group"].create(
            {
                "name": "option group for tests",
                "create_lot": True,
                "option_ids": [
                    (
                        0,
                        0,
                        {
                            "step": 1,
                            "name": "Location",
                            "field_name": "location_id",
                            "to_scan": True,
                            "required": True,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "step": 2,
                            "name": "Product",
                            "field_name": "product_id",
                            "to_scan": True,
                            "required": True,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "step": 2,
                            "name": "Packaging",
                            "field_name": "packaging_id",
                            "to_scan": True,
                            "required": False,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "step": 2,
                            "name": "Lot / Serial",
                            "field_name": "lot_id",
                            "to_scan": True,
                            "required": True,
                        },
                    ),
                ],
            }
        )

    def action_barcode_scanned(self, wizard, barcode):
        wizard._barcode_scanned = barcode
        wizard._on_barcode_scanned()
        # Method to call all methods outside of onchange environment for pickings read
        if wizard._name != "wiz.stock.barcodes.new.lot":
            wizard.dummy_on_barcode_scanned()
