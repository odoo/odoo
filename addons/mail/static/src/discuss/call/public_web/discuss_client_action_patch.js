import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
    /**
     * Checks if we are in a client action and if we have a query parameter requesting to join a call,
     * if so, the call is joined on the current discuss thread.
     */
    async restoreDiscussThread() {
        await super.restoreDiscussThread(...arguments);
        const action = this.props.action;
        if (!action) {
            return;
        }
        const call = action.context?.call || action.params?.call;
        if (call === "accept") {
            await this.rtc.joinCall(this.store.discuss.thread);
        }
    },
});
