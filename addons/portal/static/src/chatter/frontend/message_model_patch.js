import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message_model";

patch(Message.prototype, {
    get canToggleStar() {
        let result = super.canToggleStar;
        if (this.thread && this.thread.model !== "discuss.channel") {
            result = result && this.thread.hasReadAccess;
        }
        return result;
    },
});
