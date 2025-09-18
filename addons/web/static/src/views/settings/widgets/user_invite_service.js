// @ts-check

/** @module @web/views/settings/widgets/user_invite_service - Service that fetches and caches pending user invitation data from /base_setup/data */

/** Service that fetches pending user invitation data from /base_setup/data. */
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
export const userInviteService = {
    /** @returns {Promise<{ fetchData: (reload?: boolean) => Promise<Record<string, any>> }>} */
    async start() {
        /** @type {Promise<Record<string, any>> | undefined} */
        let dataProm;
        return {
            /**
             * Fetch pending user invitation data (cached unless reload is true).
             * @param {boolean} [reload=false] - Force re-fetch from server
             * @returns {Promise<Record<string, any>>}
             */
            fetchData(reload = false) {
                if (!dataProm || reload) {
                    dataProm = rpc("/base_setup/data");
                }
                return dataProm;
            },
        };
    },
};

registry.category("services").add("user_invite", userInviteService);
