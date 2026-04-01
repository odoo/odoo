import { patch } from "@web/core/utils/patch";
import { MailCoreCommon } from "@mail/core/common/mail_core_common_service";

patch(MailCoreCommon.prototype, {
    _handleNotificationToggleStar(payload, metadata) {
        super._handleNotificationToggleStar(payload, metadata);
        const { id: notifId } = metadata;
        const { message_ids: messageIds, starred } = payload;
        for (const id of messageIds) {
            const message = this.store["mail.message"].get({ id });
            const starredBox = this.store.starred;
            if (starred) {
                if (notifId > starredBox.counter_bus_id) {
                    starredBox.counter++;
                }
                starredBox.messages.add(message);
            } else {
                if (notifId > starredBox.counter_bus_id) {
                    starredBox.counter--;
                }
                starredBox.messages.delete(message);
            }
        }
    },
});
