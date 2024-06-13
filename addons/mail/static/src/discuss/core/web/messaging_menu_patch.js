import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { patch } from "@web/core/utils/patch";

Object.assign(MessagingMenu.components, { ChannelSelector });

patch(MessagingMenu.prototype, {
    beforeOpen() {
        const res = super.beforeOpen(...arguments);
        this.store.channels.fetch();
        return res;
    },
    get counter() {
        const count = super.counter;
        const channelsContribution =
            this.store.channels.status !== "fetched"
                ? this.store.initChannelsUnreadCounter
                : Object.values(this.store.Thread.records).filter(
                      (thread) =>
                          thread.displayToSelf &&
                          !thread.mute_until_dt &&
                          !this.store.settings.mute_until_dt &&
                          (thread.message_unread_counter || thread.message_needaction_counter)
                  ).length;
        // Needactions are already counted in the super call, but we want to discard them for channel so that there is only +1 per channel.
        const channelsNeedactionCounter = Object.values(this.store.Thread.records).reduce(
            (acc, thread) => {
                return (
                    acc +
                    (thread.model === "discuss.channel" ? thread.message_needaction_counter : 0)
                );
            },
            0
        );
        return count + channelsContribution - channelsNeedactionCounter;
    },
});
