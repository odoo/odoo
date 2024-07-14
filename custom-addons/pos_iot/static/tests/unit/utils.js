/** @odoo-module */

import { registry } from "@web/core/registry";
import "@point_of_sale/../tests/unit/utils";

const originalLoad = registry.category("mock_server").get("pos.session/load_pos_data");
registry.category("mock_server").add(
    "pos.session/load_pos_data",
    async function () {
        return Object.assign(await originalLoad.call(this, ...arguments), { "iot.device": [] });
    },
    { force: true }
);
