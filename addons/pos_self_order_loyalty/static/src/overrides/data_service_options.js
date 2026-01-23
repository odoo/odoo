import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "res.partner": {
                key: "id",
                condition: (record) => false,
            },
            "loyalty.card": {
                key: "uuid",
                condition: (record) =>
                    record.backLink("<-pos.order.line.coupon_id").length !== 0,
            },
        };
    },
    //TODO check if needed, I'm not sure it is
    get uniqueModels() {
        const uniqueModels = super.uniqueModels;
        uniqueModels.push("res.partner");
        return uniqueModels;
    },
});
