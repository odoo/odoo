/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    updateDataFromServer(data) {
        for (const key in data) {
            let updatedValue = data[key];
            if (key === "attribute_value_ids") {
                updatedValue ||= {};
            }

            this[key] = updatedValue;
        }
    },
});
