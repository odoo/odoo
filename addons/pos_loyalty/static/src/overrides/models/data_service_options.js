import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        const data = super.databaseTable;
        data.push({
            name: "loyalty.card",
            key: "id",
            condition: (record) => {
                return record["<-pos.order.line.coupon_id"].find(
                    (l) => !(l.order_id?.finalized && typeof l.order_id.id === "number")
                );
            },
        });
        return data;
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
