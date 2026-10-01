import { NotificationMessage } from "@mail/core/common/notification_message";

import { patch } from "@web/core/utils/patch";

/** @type {NotificationMessage} */
const notificationMessagePatch = {
    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickNotificationMessage(ev) {
        const subChannel = this.message.channelAsThreadCreationNotification;
        if (subChannel && ev.target.closest("a.o_channel_redirect")) {
            ev.preventDefault();
            const channel = await this.store["discuss.channel"].getOrFetch(subChannel.id);
            if (channel) {
                channel.openSubChannel();
                return;
            }
        }
        await super.onClickNotificationMessage(...arguments);
    },
};
patch(NotificationMessage.prototype, notificationMessagePatch);
