import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_status = undefined;
        this.livechat_failure = undefined;
        this.livechat_is_escalated = false;
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        this.note = "";
    },
});
