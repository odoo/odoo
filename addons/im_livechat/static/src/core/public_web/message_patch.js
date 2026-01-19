import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get showActions() {
        return this.props.thread?.livechat_end_dt
            ? super.showActions && this.store.has_access_livechat
            : super.showActions;
    },
});
