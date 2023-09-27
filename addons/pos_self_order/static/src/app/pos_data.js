/** @odoo-module */

import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const posDataService = {
    dependencies: ["rpc"],
    async start(env, { rpc }) {
        const result = await rpc("/pos-self/load-pos-data", {
            config_id: `${session.pos_self_order_data.pos_config_id}`,
        });
        return result;
    },
};

registry.category("services").add("pos_data", posDataService);
