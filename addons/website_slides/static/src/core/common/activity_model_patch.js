import { Activity } from "@mail/core/common/activity_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const activityPatch = patchModel(Activity, {
    setup() {
        super.setup(...arguments);
        this.request_partner_id = fields.One("res.partner");
    },
});
