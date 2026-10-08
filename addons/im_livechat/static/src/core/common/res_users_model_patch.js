import { ResUsers } from "@mail/core/common/res_users_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const resUsersPatch = patchModel(ResUsers, {
    setup() {
        super.setup(...arguments);
        this.is_livechat_manager = false;
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
    },
});
