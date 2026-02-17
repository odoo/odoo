import { DiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { patch } from "@web/core/utils/patch";

patch(DiscussCoreCommon.prototype, {
    _handleNotificationChannelDelete(thread, metadata) {
        const { notifId } = metadata;
        const filteredBookmarkedMessages = [];
        let bookmarkedCounter = 0;
        for (const msg of this.store.bookmarkBox.messages) {
            if (!msg.thread?.eq(thread)) {
                filteredBookmarkedMessages.push(msg);
            } else {
                bookmarkedCounter++;
            }
        }
        this.store.bookmarkBox.messages = filteredBookmarkedMessages;
        if (notifId > this.store.bookmarkBox.counter_bus_id) {
            this.store.bookmarkBox.counter -= bookmarkedCounter;
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
        if (thread.discussAppAsThread) {
            this.store.discuss.thread = undefined;
        }
        super._handleNotificationChannelDelete(thread, metadata);
    },
});
