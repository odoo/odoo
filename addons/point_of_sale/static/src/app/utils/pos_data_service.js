/** @odoo-module */

import { registry } from "@web/core/registry";

export const posDataService = {
    dependencies: ["orm"],
    async start(env, { orm }) {
        return orm.silent.call("pos.session", "load_pos_data", [[odoo.pos_session_id]]);
    },
};

registry.category("services").add("pos_data", posDataService);
