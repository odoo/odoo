import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return [
            {
                name: "pos.order",
                key: "uuid",
                condition: (record) => false,
            },
            {
                name: "pos.order.line",
                key: "uuid",
                condition: (record) => false,
            },
        ];
    },
});
