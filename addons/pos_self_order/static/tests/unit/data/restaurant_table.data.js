import { patch } from "@web/core/utils/patch";
import { RestaurantTable } from "@pos_restaurant/../tests/unit/data/restaurant_table.data";

patch(RestaurantTable.prototype, {
    _load_pos_self_data_fields() {
        return ["table_number", "identifier", "floor_id"];
    },
});

RestaurantTable._records = RestaurantTable._records.map((record) => ({
    ...record,
    identifier: String(record.id),
}));
