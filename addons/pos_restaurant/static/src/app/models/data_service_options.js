import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "restaurant.order.course": {
                key: "uuid",
                condition: (record) =>
                    record.order_id?.finalized && typeof record.order_id.id === "number",
            },
        };
    },
    get cascadeDeleteModels() {
        return [...super.cascadeDeleteModels, "restaurant.order.course"];
    },
});
