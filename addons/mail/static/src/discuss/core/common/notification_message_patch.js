import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { NotificationMessage } from "@mail/core/common/notification_message";

import { patch } from "@web/core/utils/patch";

/** @type {NotificationMessage} */
const notificationMessagePatch = {
    setup() {
        super.setup(...arguments);
        this.ancestors = useAncestors();
    },
    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickNotificationMessage(ev) {
        const { oeType } = ev.target.dataset;
        if (oeType === "pin-menu") {
            this.ancestors.threadActions?.get("pinned-messages")?.openPanel({ keepPrevious: true });
        }
        await super.onClickNotificationMessage(...arguments);
    },
};
patch(NotificationMessage.prototype, notificationMessagePatch);
