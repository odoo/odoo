/** @odoo-modules */

import { registry } from "@web/core/registry";

export const demoDataService = {
    dependencies: ["rpc"],
    async start(env, { rpc }) {
        let isDemoDataActiveProm;
        return {
            isDemoDataActive() {
                if (!isDemoDataActiveProm) {
                    isDemoDataActiveProm = rpc("/base_setup/demo_active");
                }
                return isDemoDataActiveProm;
            },
        };
    },
};

registry.category("services").add("demo_data", demoDataService);
