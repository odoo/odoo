// @ts-check

/** @module @web/views/settings/widgets/demo_data_service - Service that checks whether demo data is active in the current database */

/** Service that checks whether demo data is active in the current database. */
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
export const demoDataService = {
    /** @returns {Promise<{ isDemoDataActive: () => Promise<boolean> }>} */
    async start() {
        /** @type {Promise<boolean> | undefined} */
        let isDemoDataActiveProm;
        return {
            /**
             * Check whether demo data is installed (cached after first call).
             * @returns {Promise<boolean>}
             */
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
