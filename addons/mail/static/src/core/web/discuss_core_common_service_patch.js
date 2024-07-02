import { DiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { patch } from "@web/core/utils/patch";

patch(DiscussCoreCommon.prototype, {
    _handleNotificationChannelDelete(thread, metadata) {
        const { notifId } = metadata;
        const filteredStarredMessages = [];
        let starredCounter = 0;
        for (const msg of this.store.discuss.starred.messages) {
            if (!msg.thread?.eq(thread)) {
                filteredStarredMessages.push(msg);
            } else {
                starredCounter++;
            }
        }
        this.store.discuss.starred.messages = filteredStarredMessages;
        if (notifId > this.store.discuss.starred.counter_bus_id) {
            this.store.discuss.starred.counter -= starredCounter;
        }
        this.store.discuss.inbox.messages = this.store.discuss.inbox.messages.filter(
            (msg) => !msg.thread?.eq(thread)
        );
        if (notifId > this.store.discuss.inbox.counter_bus_id) {
            this.store.discuss.inbox.counter -= thread.message_needaction_counter;
        }
        this.store.discuss.history.messages = this.store.discuss.history.messages.filter(
            (msg) => !msg.thread?.eq(thread)
        );
        if (thread.eq(this.store.discuss.thread)) {
            this.store.discuss.inbox.setAsDiscussThread();
        }
        super._handleNotificationChannelDelete(thread, metadata);
    },
});
