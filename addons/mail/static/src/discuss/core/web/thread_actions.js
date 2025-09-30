import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

export const joinChannelAction = {
    condition: ({ thread }) =>
        thread &&
        !thread.self_member_id &&
        !["chat", "group"].includes(thread.channel_type) &&
        thread.model !== "mail.box",
    open: ({ store, thread }) =>
        store.env.services.orm.call("discuss.channel", "add_members", [[thread.id]], {
            partner_ids: [store.self.id],
        }),
    icon: "fa fa-fw fa-sign-in",
    name: _t("Join Channel"),
    sequence: 20,
    sequenceGroup: ({ owner }) => (owner.isDiscussContent ? undefined : 5),
    tags: [ACTION_TAGS.SUCCESS],
};
registerThreadAction("join-channel", joinChannelAction);
registerThreadAction("expand-discuss", {
    condition: ({ owner, store, thread }) =>
        thread &&
        owner.props.chatWindow?.isOpen &&
        thread.model === "discuss.channel" &&
        !store.env.services.ui.isSmall &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Discuss"),
    open({ owner, store, thread }) {
        store.env.services.action.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            {
                clearBreadcrumbs: owner.env.services["home_menu"]?.hasHomeMenu,
                additionalContext: { active_id: thread.id },
            }
        );
    },
    sequence: 10,
    sequenceGroup: 5,
});
registerThreadAction("advanced-settings", {
    condition: ({ owner, thread }) => thread && owner.isDiscussSidebarChannelActions,
    open: ({ owner, store, thread }) => {
        store.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "discuss.channel",
            views: [[false, "form"]],
            res_id: thread.id,
            target: "current",
        });
    },
    icon: "fa fa-fw fa-gear",
    name: _t("Advanced Settings"),
    sequence: 20,
    sequenceGroup: 30,
});
