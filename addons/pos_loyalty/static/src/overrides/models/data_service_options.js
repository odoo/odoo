import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "loyalty.card": {
                key: "id",
                condition: (record) => {
                    return record.models["pos.order.line"].find(
                        (l) => l.coupon_id?.id === record.id
                    );
                },
            },
        };
    },
});
