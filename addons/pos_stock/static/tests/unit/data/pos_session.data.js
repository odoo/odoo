import { patch } from "@web/core/utils/patch";
import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";

patch(PosSession.prototype, {
    _load_pos_data_models(config_id) {
        return [
            ...super._load_pos_data_models(config_id),
            "pos.pack.operation.lot",
            "stock.picking.type",
        ];
    },

    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "update_stock_at_closing"];
    },
});
