import { DiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { patch } from "@web/core/utils/patch";

patch(DiscussCoreCommon.prototype, {
    _handleNotificationChannelDelete(channel, metadata) {
        const { notifId } = metadata;
        const filteredStarredMessages = [];
        let starredCounter = 0;
        for (const msg of this.store.starred.messages) {
            if (!msg.channel_id?.eq(channel)) {
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
            (msg) => !msg.channel_id?.eq(channel)
        );
        if (notifId > this.store.inbox.counter_bus_id) {
            this.store.inbox.counter -= channel.message_needaction_counter;
        }
        this.store.history.messages = this.store.history.messages.filter(
            (msg) => !msg.channel_id?.eq(channel)
        );
        if (channel.discussAppAsThread) {
            this.store.discuss.thread = undefined;
        }
        super._handleNotificationChannelDelete(channel, metadata);
    },
});
