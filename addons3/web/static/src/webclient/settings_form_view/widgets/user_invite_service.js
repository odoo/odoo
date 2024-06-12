/** @odoo-modules */

import { registry } from "@web/core/registry";

export const userInviteService = {
    dependencies: ["rpc"],
    async start(env, { rpc }) {
        let dataProm;
        return {
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
