import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "res.partner": {
                key: "id",
                condition: (record) => record.order_id?.canBeRemovedFromIndexedDB,
            },
        };
    },
});
