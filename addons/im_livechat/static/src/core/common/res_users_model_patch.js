import { ResUsers } from "@mail/core/common/res_users_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResUsers} */
const resUsersPatch = {
    setup() {
        super.setup(...arguments);
        this.is_livechat_manager = false;
    },
};
patch(ResUsers.prototype, resUsersPatch);
