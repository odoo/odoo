import { NotificationMessage } from "@mail/core/common/notification_message";

import { patch } from "@web/core/utils/patch";

patch(NotificationMessage.prototype, {
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
