import { fields, patchModel } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";

export const threadPatch = patchModel(Thread, {
    setup() {
        super.setup(...arguments);
        this.livechat_visitor_id = fields.One("website.visitor");
    },
});
