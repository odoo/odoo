import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get hasLeadAction() {
        return this.channel_type === "livechat" || super.hasLeadAction;
    },
});
