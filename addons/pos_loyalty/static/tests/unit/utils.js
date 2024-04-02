/** @odoo-module */

import { MockPosData } from "@point_of_sale/../tests/unit/pos_app_tests";
import { patch } from "@web/core/utils/patch";

patch(MockPosData.prototype, {
    get data() {
        const data = super.data;
        data["models"]["loyalty.reward"] = { relations: {}, fields: {}, data: [] };
        data["models"]["loyalty.program"] = { relations: {}, fields: {}, data: [] };
        return data;
    },
});
