import { fields, models } from "@web/../tests/web_test_helpers";

export class StockPicking extends models.Model {
    name = fields.Char();
    move_line_ids = fields.One2many({ relation: "stock.move.line" });
    location_id = fields.Many2one({ relation: "stock.location" });
    location_dest_id = fields.Many2one({ relation: "stock.location" });
    picking_type_id = fields.Many2one({ relation: "stock.picking.type" });
    user_id = fields.Many2one({ relation: "res.users" });
    _records = [
        {
            id: 1,
            name: "TEST/IN/0001",
            move_line_ids: [2],
            location_id: 5,
            location_dest_id: 6,
            picking_type_id: 1,
        },
    ];
}
