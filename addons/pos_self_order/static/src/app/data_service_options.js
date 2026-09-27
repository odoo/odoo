import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            "pos.order": {
                key: "uuid",
                condition: (record) => false,
            },
            "pos.order.line": {
                key: "uuid",
                condition: (record) => false,
            },
            "pos.payment": {
                key: "uuid",
                condition: (record) => false,
            },
            "pos.payment.method": {
                key: "id",
                condition: (record) => false,
            },
            "restaurant.order.course": {
                key: "uuid",
                condition: (record) => false,
            },
            "pos.prep.order": {
                key: "uuid",
                condition: (record) => false,
            },
            "pos.prep.line": {
                key: "uuid",
                condition: (record) => false,
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
