/** @odoo-module */

import "@point_of_sale/../tests/unit/utils";
import { registry } from "@web/core/registry";

const loadPosData = registry.category("mock_server").get("pos.session/load_pos_data");

registry.category("mock_server").add(
    "pos.session/load_pos_data",
    async function () {
        const res = await loadPosData.call(this, ...arguments);
        res["pos_preparation_display.display"] = [];
        return res;
    },
    { force: true }
);
