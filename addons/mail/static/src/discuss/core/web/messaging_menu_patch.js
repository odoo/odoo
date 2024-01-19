/* @odoo-module */

import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { patch } from "@web/core/utils/patch";

Object.assign(MessagingMenu.components, { ChannelSelector });

patch(MessagingMenu.prototype, {
    beforeOpen() {
        const res = super.beforeOpen(...arguments);
        this.store.fetchChannels();
        return res;
    },
    get counter() {
        const count = super.counter;
        const channelsContribution =
            this.store.fetchChannelsState !== "fetched"
                ? this.store.initChannelsUnreadCounter
                : Object.values(this.store.Thread.records).filter(
                      (thread) => thread.displayToSelf && thread.message_unread_counter > 0
                  ).length;
        return count + channelsContribution;
    },
});
