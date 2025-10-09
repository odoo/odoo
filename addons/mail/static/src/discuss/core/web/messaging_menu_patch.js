import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

Object.assign(MessagingMenu.components, { DiscussSearch });

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.command = useService("command");
    },
    beforeOpen() {
        const res = super.beforeOpen(...arguments);
        this.store.channels.fetch();
        return res;
    },
    onClickNewMessage() {
        this.command.openMainPalette({ searchValue: "@" });
        if (!this.ui.isSmall && !this.env.inDiscussApp) {
            this.dropdown.close();
        }
    },
    get counter() {
        const count = super.counter;
        const channelsContribution =
            this.store.channels.status !== "fetched"
                ? this.store.initChannelsUnreadCounter
                : Object.values(this.store["discuss.channel"].records).filter(
                      (channel) =>
                          channel.displayToSelf &&
                          !channel.self_member_id?.mute_until_dt &&
                          (channel.self_member_id?.message_unread_counter ||
                              channel.message_needaction_counter)
                  ).length;
        // Needactions are already counted in the super call, but we want to discard them for channel so that there is only +1 per channel.
        const channelsNeedactionCounter = Object.values(
            this.store["discuss.channel"].records
        ).reduce((acc, channel) => acc + channel.message_needaction_counter, 0);
        return count + channelsContribution - channelsNeedactionCounter;
    },
});
