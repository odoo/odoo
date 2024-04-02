/** @odoo-module */

import { MockPosData } from "@point_of_sale/../tests/unit/pos_app_tests";
import { patch } from "@web/core/utils/patch";

patch(MockPosData.prototype, {
    get data() {
        const data = super.data;
        data["models"]["sale.order"] = { relations: {}, fields: {}, data: [] };
        data["models"]["sale.order.line"] = { relations: {}, fields: {}, data: [] };
        return data;
    },
});
