import { DiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { patch } from "@web/core/utils/patch";

patch(DiscussCoreCommon.prototype, {
    _handleNotificationChannelDelete(thread, metadata) {
        const { notifId } = metadata;
        const filteredStarredMessages = [];
        let starredCounter = 0;
        for (const msg of this.store.starred.messages) {
            if (!msg.thread?.eq(thread)) {
                filteredStarredMessages.push(msg);
            } else {
                starredCounter++;
            }
        }
        this.store.starred.messages = filteredStarredMessages;
        if (notifId > this.store.starred.counter_bus_id) {
            this.store.starred.counter -= starredCounter;
        }
        this.store.inbox.messages = this.store.inbox.messages.filter(
            (msg) => !msg.thread?.eq(thread)
        );
        if (notifId > this.store.inbox.counter_bus_id) {
            this.store.inbox.counter -= thread.message_needaction_counter;
        }
        this.store.history.messages = this.store.history.messages.filter(
            (msg) => !msg.thread?.eq(thread)
        );
        if (thread.eq(this.store.discuss.thread)) {
            this.store.inbox.setAsDiscussThread();
        }
        super._handleNotificationChannelDelete(thread, metadata);
    },
});
