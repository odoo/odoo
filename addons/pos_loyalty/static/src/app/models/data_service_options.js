import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "loyalty.card": {
                key: "id",
                condition: (record) =>
                    record
                        .backLink("<-pos.order.line.coupon_id")
                        .find((l) => !(l.order_id?.finalized && l.order_id.isSynced)),
            },
        };
    },
    get pohibitedAutoLoadedModels() {
        return [
            ...super.pohibitedAutoLoadedModels,
            "loyalty.program",
            "loyalty.rule",
            "loyalty.reward",
        ];
    },
    get cleanupModels() {
        return [...super.cleanupModels, "loyalty.program"];
    },
});
