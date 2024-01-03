/** @odoo-module */

import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        const data = super.databaseTable;
        data.push({
            name: "sale.order",
            key: "id",
            condition: (record) => {
                return record.models["pos.order.line"].find(
                    (l) => l.sale_order_origin_id?.id === record.id
                );
            },
        });
        data.push({
            name: "sale.order.line",
            key: "id",
            condition: (record) => {
                return record.models["pos.order.line"].find(
                    (l) => l.sale_order_line_id?.id === record.id
                );
            },
        });
        return data;
    },
});
