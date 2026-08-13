import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

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
