import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "restaurant.order.course": {
                key: "uuid",
                condition: (record) => record.order_id?.finalized && record.order_id.isSynced,
            },
        };
    },
    get cascadeDeleteModels() {
        return [...super.cascadeDeleteModels, "restaurant.order.course"];
    },
    get dynamicModels() {
        return [...super.dynamicModels, "restaurant.order.course"];
    },
});
