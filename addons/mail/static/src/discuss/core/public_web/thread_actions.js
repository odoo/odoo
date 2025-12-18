import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { useChildSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("show-threads", {
    actionPanelClose: ({ action }) => action.popover?.close(),
    actionPanelComponent: SubChannelList,
    actionPanelComponentProps: ({ action, thread }) => ({
        close: () => action.actionPanelClose(),
        thread,
    }),
    actionPanelOpen({ channel, owner }) {
        this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), {
            thread: (channel?.parent_channel_id || channel).thread,
        });
    },
    actionPanelOuterClass: "bg-100 border border-secondary",
    condition: ({ channel, owner }) =>
        (channel?.hasSubChannelFeature || channel?.parent_channel_id?.hasSubChannelFeature) &&
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
