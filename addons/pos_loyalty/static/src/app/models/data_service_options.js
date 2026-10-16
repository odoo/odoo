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
                        .backLink("<-pos.order.line.card_id")
                        .filter((l) => !l.order_id?.canBeRemovedFromIndexedDB).length === 0,
                getRecordsBasedOnLines: (orderlines) =>
                    orderlines.map((line) => line.card_id).filter((c) => c),
            },
        };
    },
    get cleanupIgnoredReferences() {
        // Only used to print the coupons created by the order on its receipt
        return [...super.cleanupIgnoredReferences, "loyalty.card.source_pos_order_id"];
    },
    get prohibitedAutoLoadedModels() {
        return [
            ...super.prohibitedAutoLoadedModels,
            "loyalty.program",
            "loyalty.rule",
            "loyalty.reward",
        ];
    },
});
