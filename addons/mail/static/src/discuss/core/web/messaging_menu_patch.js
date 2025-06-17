import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.command = useService("command");
    },
    beforeOpen() {
        const res = super.beforeOpen(...arguments);
        if (!this.state.tabState["channel"][1] || !this.state.tabState["chat"][1]) {
            const currentState = this.store.channels;
            const limited_channels = this.store.makeCachedFetchData("channels_as_member", {
                limit: this.store.FETCH_LIMIT,
            });
            this.store.channels = limited_channels;
            // Wait for fetch to complete before restoring
            limited_channels.fetch().then(() => {
                this.store.channels = currentState;
            });
        }
        return res;
    },
    onClickNewMessage() {
        this.command.openMainPalette({ searchValue: "@" });
        if (!this.ui.isSmall && !this.env.inDiscussApp) {
            this.dropdown.close();
        }
    },
    get channelsContributionCount() {
        const threads = Object.values(this.store.Thread.records).filter(
            (thread) =>
                thread.displayToSelf &&
                !thread.isMuted &&
                (thread.selfMember?.message_unread_counter || thread.message_needaction_counter)
        );
        if (!this.store.initChannelsUnreadCounter) {
            return threads.length;
        }
        if (
            this.store.channels.status !== "fetched"
        ) {
            return this.store.initChannelsUnreadCounter;
        }
        return threads.length;
    },
    get counter() {
        const count = super.counter;
        const channelsContribution = this.channelsContributionCount;
        const channelsNeedactionCounter = Object.values(this.store.Thread.records).reduce(
            (acc, thread) =>
                acc + (thread.model === "discuss.channel" ? thread.message_needaction_counter : 0),
            0
        );
        return count + channelsContribution - channelsNeedactionCounter;
    },
});
