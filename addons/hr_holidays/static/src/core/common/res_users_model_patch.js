import { ResUsers } from "@mail/core/common/res_users_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResUsers} */
const resUsersPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {string} */
        this.leave_date_to = undefined;
    },
};
patch(ResUsers.prototype, resUsersPatch);
