import { fields, models } from "@web/../tests/web_test_helpers";

export class StockMoveLine extends models.Model {
    product_id = fields.Many2one({ relation: "product.product" });
    product_uom_id = fields.Many2one({ relation: "uom.uom" });
    location_id = fields.Many2one({ relation: "stock.location" });
    location_dest_id = fields.Many2one({ relation: "stock.location" });
    expiration_date = fields.Datetime();
    qty_done = fields.Integer();
    quantity = fields.Integer();
    lot_name = fields.Char();
    _records = [
        {
            id: 2,
            product_id: 3,
            product_uom_id: 4,
            location_id: 5,
            location_dest_id: 6,
            expiration_date: "2025-06-15 23:30:00",
            qty_done: 1,
            quantity: 1,
            lot_name: "TEST LOT",
        },
    ];
}
