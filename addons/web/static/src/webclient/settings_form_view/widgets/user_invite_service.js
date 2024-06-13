import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export const userInviteService = {
    async start() {
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
