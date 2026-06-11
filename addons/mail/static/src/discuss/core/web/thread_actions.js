import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

export const expandDiscussSequenceGroup = 5;
export const expandDiscussSequenceQuick = 0;

export const joinChannelAction = {
    condition: ({ channel }) =>
        channel && !channel.self_member_id && !["chat", "group"].includes(channel.channel_type),
    onSelected: ({ channel, store }) =>
        store.fetchStoreData("/discuss/channel/add_members", {
            channel_id: channel.id,
            user_ids: [store.self_user.id],
        }),
    icon: "fa fa-fw fa-sign-in",
    name: _t("Join Channel"),
    sequence: 20,
    sequenceGroup: ({ isDiscussContent }) => (isDiscussContent ? undefined : 5),
    tags: [ACTION_TAGS.PRIMARY],
};
registerThreadAction("join-channel", joinChannelAction);
registerThreadAction("expand-discuss", {
    condition: ({ channel, chatWindow, isDiscussSidebarChannelActions, store }) =>
        channel &&
        chatWindow?.isOpen &&
        !store.env.services.ui.isSmall &&
        !isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Discuss"),
    onSelected({ channel, homeMenuHasHomeMenu, store }) {
        store.env.services.action.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            {
                clearBreadcrumbs: homeMenuHasHomeMenu,
                additionalContext: { active_id: channel.id },
            }
        );
    },
    sequence: 10,
    sequenceGroup: expandDiscussSequenceGroup,
    sequenceQuick: expandDiscussSequenceQuick,
});
registerThreadAction("advanced-settings", {
    condition: ({ channel, isDiscussContent }) =>
        ["owner", "admin"].includes(channel?.self_member_id?.channel_role) && !isDiscussContent,
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
