import { Activity } from "@mail/core/common/activity_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Activity} */
const activityPatch = {
    setup() {
        super.setup(...arguments);
        this.request_partner_id = fields.One("res.partner");
    },
};
patch(Activity.prototype, activityPatch);
