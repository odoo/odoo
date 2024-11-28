import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "loyalty.card": {
                key: "id",
                condition: (record) => {
                    return record["<-pos.order.line.coupon_id"].find(
                        (l) => !(l.order_id?.finalized && typeof l.order_id.id === "number")
                    );
                },
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
});
