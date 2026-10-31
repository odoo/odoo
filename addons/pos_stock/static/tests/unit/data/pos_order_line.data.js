import { patch } from "@web/core/utils/patch";
import { PosOrderLine } from "@point_of_sale/../tests/unit/data/pos_order_line.data";

patch(PosOrderLine.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "pack_lot_ids"];
    },
    get_existing_lots(compagny_id, config_id, product_id) {
        if (product_id !== 27) {
            return Promise.reject({
                message: "Odoo Server Error",
                data: {
                    message: "No PoS configuration found",
                    type: "server_exception",
                },
            });
        }

        return [
            {
                id: 1,
                lot_name: "lot1",
                expiration_date: "2027-01-01",
                product_qty: 1,
                name: "lot1",
            },
            {
                id: 2,
                lot_name: "lot2",
                expiration_date: "2029-01-01",
                product_qty: 1,
                name: "lot2",
            },
        ];
    },
});
