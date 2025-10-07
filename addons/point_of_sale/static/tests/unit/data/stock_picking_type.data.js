import { models } from "@web/../tests/web_test_helpers";

export class StockPickingType extends models.ServerModel {
    _name = "stock.picking.type";

    _load_pos_data_fields() {
        return ["id", "use_create_lots", "use_existing_lots"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 9,
            use_create_lots: true,
            use_existing_lots: true,
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
