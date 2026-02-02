import { registerThreadAction } from "@mail/core/common/thread_actions";
import { NO_MEMBERS_DEFAULT_OPEN_LS } from "@mail/core/public_web/discuss_app_model";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";

import { useChildSubEnv } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
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
registerThreadAction("member-list", {
    actionPanelComponent: ChannelMemberList,
    actionPanelComponentProps: ({ owner }) => ({
        openChannelInvitePanel({ keepPrevious } = {}) {
            owner.threadActions.actions
                .find(({ id }) => id === "invite-people")
                ?.open({ keepPrevious });
        },
    }),
    condition: ({ owner, thread }) =>
        thread?.hasMemberList &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    panelOuterClass: "o-discuss-ChannelMemberList bg-inherit",
    icon: "oi oi-fw oi-users",
    name: _t("Members"),
    close: ({ action, nextActiveAction, owner, store }) => {
        if (
            action.condition &&
            owner.env.inDiscussApp &&
            store.discuss?.shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction)
        ) {
            browser.localStorage.setItem(NO_MEMBERS_DEFAULT_OPEN_LS, true);
            store.discuss._recomputeIsMemberPanelOpenByDefault++;
        }
    },
    open: ({ owner, store }) => {
        if (owner.env.inDiscussApp) {
            browser.localStorage.removeItem(NO_MEMBERS_DEFAULT_OPEN_LS);
            store.discuss._recomputeIsMemberPanelOpenByDefault++;
        }
    },
    sequence: 30,
    sequenceGroup: 10,
    toggle: true,
});
