/** @odoo-module */

import { MockPosData } from "@point_of_sale/../tests/unit/pos_app_tests";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

patch(MockPosData.prototype, {
    get data() {
        const data = super.data;
        data.models["pos.config"]["fields"]["currency_id"] = {
            string: "Currency",
            type: "many2one",
            relation: "res.currency",
            store: true,
        };
        data.models["pos.config"]["data"].forEach((rec) => {
            rec["currency_id"] = 1;
        });
        data.models["res.currency"]["data"][0]["id"] = 1;
        return data;
    },
});

registry
    .category("mock_server")
    .add("res.partner/get_all_total_due", async function (route, { args }) {
        return [];
    });
