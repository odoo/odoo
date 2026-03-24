import { ResUsers } from "@mail/../tests/mock_server/mock_models/res_users";

import { serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

const resUsersPatch = {
    _init_store_data(store) {
        super._init_store_data(...arguments);
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        store.add_global_values((res) => {
            res.attr(
                "has_access_create_lead",
                this.env.user?.group_ids.includes(serverState.groupSalesTeamId)
            );
            res.attr(
                "channel_types_with_create_lead",
                DiscussChannel._types_allowing_create_lead()
            );
        });
    },
};

patch(ResUsers.prototype, resUsersPatch);
