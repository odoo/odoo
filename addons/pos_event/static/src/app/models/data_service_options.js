import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "event.registration": {
                key: "id",
                condition: (record) => {
                    return (
                        !record.pos_order_line_id || record.pos_order_line_id?.order_id?.finalized
                    );
                },
            },
            "event.registration.answer": {
                key: "id",
                condition: (record) => {
                    return (
                        !record.registration_id ||
                        record.registration_id?.pos_order_line_id?.order_id?.finalized
                    );
                },
            },
        };
    },
    get dynamicModels() {
        return [...super.dynamicModels, "event.registration", "event.registration.answer"];
    },
});
