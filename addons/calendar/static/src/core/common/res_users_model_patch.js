import { ResUsers } from "@mail/core/common/res_users_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

patch(ResUsers.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_in_meeting = fields.Attr(false);
    },
});
