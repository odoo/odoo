import { ResUsers } from "@mail/core/common/res_users_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResUsers} */
const resUsersPatch = {
    setup() {
        super.setup(...arguments);
        this.is_livechat_manager = false;
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
    },
};
patch(ResUsers.prototype, resUsersPatch);
