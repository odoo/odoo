import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export const demoDataService = {
    async start() {
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
