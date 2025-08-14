import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { useChildSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("show-threads", {
    actionPanelComponent: SubChannelList,
    actionPanelComponentProps: ({ action }) => ({ close: () => action.close() }),
    close: ({ action }) => action.popover?.close(),
    condition: ({ owner, thread }) =>
        (thread?.hasSubChannelFeature || thread?.parent_channel_id?.hasSubChannelFeature) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-comments-o",
    name: _t("Threads"),
    setup({ owner, store }) {
        if (owner.env.inDiscussApp && !store.env.isSmall) {
            this.popover = usePopover(SubChannelList, {
                onClose: () => this.close(),
                fixedPosition: true,
                popoverClass: this.panelOuterClass,
            });
        }
        useChildSubEnv({ subChannelMenu: { open: () => this.open() } });
    },
    open({ owner, thread }) {
        const channel = thread?.parent_channel_id || thread;
        this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), { thread: channel });
    },
    panelOuterClass: "bg-100 border border-secondary",
    sequence: ({ owner }) => (owner.props.chatWindow ? 40 : 5),
    sequenceGroup: 10,
    toggle: true,
});
