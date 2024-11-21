import { Message } from "@mail/core/common/message";
import { Poll } from "@mail/discuss/core/public_web/poll_component";
import { PollResult } from "@mail/discuss/core/public_web/poll_result";
import { patch } from "@web/core/utils/patch";

Message.components = { ...Message.components, Poll, PollResult };
patch(Message.prototype, {
    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickNotificationMessage(ev) {
        const { oeType } = ev.target.dataset;
        if (oeType === "sub-channels-menu") {
            this.env.subChannelMenu?.open();
        }
        await super.onClickNotificationMessage(...arguments);
    },
});
