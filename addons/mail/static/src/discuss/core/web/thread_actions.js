import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

export const joinChannelAction = {
    condition: ({ channel }) =>
        channel && !channel.self_member_id && !["chat", "group"].includes(channel.channel_type),
    onSelected: ({ channel, store }) =>
        store.env.services.orm.call("discuss.channel", "add_members", [[channel.id]], {
            partner_ids: [store.self_user?.partner_id?.id],
        }),
    icon: "fa fa-fw fa-sign-in",
    name: _t("Join Channel"),
    sequence: 20,
    sequenceGroup: ({ owner }) => (owner.isDiscussContent ? undefined : 5),
    tags: [ACTION_TAGS.SUCCESS],
};
registerThreadAction("join-channel", joinChannelAction);
registerThreadAction("expand-discuss", {
    condition: ({ channel, owner, store }) =>
        channel &&
        owner.props.chatWindow?.isOpen &&
        !store.env.services.ui.isSmall &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Discuss"),
    onSelected({ owner, store, thread }) {
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
    condition: ({ channel, owner }) => channel && owner.isDiscussSidebarChannelActions,
    onSelected: ({ channel, store }) => {
        store.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "discuss.channel",
            views: [[false, "form"]],
            res_id: channel.id,
            target: "current",
        });
    },
    icon: "fa fa-fw fa-gear",
    name: _t("Advanced Settings"),
    sequence: 20,
    sequenceGroup: 30,
});
