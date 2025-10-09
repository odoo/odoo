import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { useChildSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("show-threads", {
    actionPanelClose: ({ action }) => action.popover?.close(),
    actionPanelComponent: SubChannelList,
    actionPanelComponentProps: ({ action }) => ({ close: () => action.actionPanelClose() }),
    actionPanelOpen({ owner, thread }) {
        const channel = thread?.parent_channel_id || thread;
        this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), { thread: channel });
    },
    actionPanelOuterClass: "bg-100 border border-secondary",
    condition: ({ owner, thread }) =>
        (thread?.hasSubChannelFeature || thread?.parent_channel_id?.hasSubChannelFeature) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-comments-o",
    name: _t("Threads"),
    setup({ owner, store }) {
        if (owner.env.inDiscussApp && !store.env.isSmall) {
            this.popover = usePopover(SubChannelList, {
                onClose: () => this.actionPanelClose(),
                fixedPosition: true,
                popoverClass: this.actionPanelOuterClass,
            });
        }
        useChildSubEnv({ subChannelMenu: { open: () => this.actionPanelOpen() } });
    },
    sequence: ({ owner }) => (owner.props.chatWindow ? 40 : 5),
    sequenceGroup: 10,
});
registerThreadAction("leave", {
    condition: ({ owner, thread }) => thread?.canLeave && !owner.isDiscussContent,
    icon: "fa fa-fw fa-sign-out",
    name: _t("Leave Channel"),
    open: ({ thread }) => thread.leaveChannel(),
    partition: ({ owner }) => owner.env.inChatWindow,
    sequence: 10,
    sequenceGroup: 40,
    tags: ACTION_TAGS.DANGER,
});
registerThreadAction("unpin", {
    condition: ({ owner, thread }) => thread?.canUnpin && !owner.isDiscussContent,
    icon: "fa fa-fw fa-thumb-tack",
    name: _t("Unpin Conversation"),
    open: ({ thread }) => thread.channelPin(false),
    partition: ({ owner }) => owner.env.inChatWindow,
    sequence: 20,
    sequenceGroup: 50,
    tags: ACTION_TAGS.DANGER,
});
