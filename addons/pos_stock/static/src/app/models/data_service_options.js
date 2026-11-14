import { patch } from "@web/core/utils/patch";
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "pos.pack.operation.lot": {
                key: "uuid",
                condition: (record) =>
                    record.pos_order_line_id?.order_id?.canBeRemovedFromIndexedDB,
                getRecordsBasedOnLines: (orderlines) =>
                    orderlines.flatMap((line) => line.pack_lot_ids),
            },
        };
    },

    get dynamicModels() {
        return ["pos.pack.operation.lot", ...super.dynamicModels];
    },

    get cascadeDeleteModels() {
        return ["pos.pack.operation.lot", ...super.cascadeDeleteModels];
    },
});
