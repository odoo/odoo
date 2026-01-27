import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { NO_MEMBERS_DEFAULT_OPEN_LS } from "@mail/core/public_web/discuss_app_model";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";

import { useComponent } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

threadActionsRegistry
    .add("leave", {
        condition: (component) =>
            component.ui.isSmall && (component.thread?.canLeave || component.thread?.canUnpin),
        icon: "fa fa-fw fa-sign-out text-danger",
        name: (component) => (component.thread.canLeave ? _t("Leave") : _t("Unpin")),
        nameClass: "text-danger",
        open: (component) =>
            component.thread.canLeave ? component.thread.leaveChannel() : component.thread.unpin(),
        sequence: 10,
        sequenceGroup: 40,
        setup() {
            const component = useComponent();
            component.ui = useService("ui");
        },
    })
    .add("member-list", {
        component: ChannelMemberList,
        condition(component) {
            return (
                component.thread?.hasMemberList &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        componentProps(action, component) {
            return {
                openChannelInvitePanel({ keepPrevious } = {}) {
                    component.threadActions.actions
                        .find(({ id }) => id === "invite-people")
                        ?.open({ keepPrevious });
                },
            };
        },
        panelOuterClass: "o-discuss-ChannelMemberList bg-inherit",
        icon: "fa fa-fw fa-users",
        iconLarge: "fa fa-fw fa-lg fa-users",
        name: _t("Members"),
        close(component) {
            if (component.env.inDiscussApp) {
                browser.localStorage.setItem(NO_MEMBERS_DEFAULT_OPEN_LS, true);
                component.store.discuss._recomputeIsMemberPanelOpenByDefault++;
            }
        },
        open(component) {
            if (component.env.inDiscussApp) {
                browser.localStorage.removeItem(NO_MEMBERS_DEFAULT_OPEN_LS);
                component.store.discuss._recomputeIsMemberPanelOpenByDefault++;
            }
        },
        sequence: 30,
        sequenceGroup: 10,
        toggle: true,
    });
