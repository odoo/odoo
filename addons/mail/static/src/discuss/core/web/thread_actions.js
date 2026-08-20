import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

export const expandDiscussSequenceGroup = 5;
export const expandDiscussSequenceQuick = 0;

registerThreadAction("expand-discuss", {
    condition: ({ channel, owner, store }) =>
        channel &&
        owner.props.chatWindow?.isOpen &&
        !store.env.services.ui.isSmall &&
        !owner.isDiscussSidebarChannelActions,
    icon: "expand_content",
    name: _t("Open in Discuss"),
    onSelected({ channel, store }) {
        store.env.services.action.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            {
                clearBreadcrumbs: true,
                additionalContext: { active_id: channel.id },
            }
        );
    },
    sequence: 10,
    sequenceGroup: expandDiscussSequenceGroup,
    sequenceQuick: expandDiscussSequenceQuick,
});
registerThreadAction("advanced-settings", {
    condition: ({ channel, owner }) =>
        ["owner", "admin"].includes(channel?.self_member_id?.channel_role) &&
        !owner.isDiscussContent,
    onSelected: ({ channel, store }) => {
        store.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "discuss.channel",
            views: [[false, "form"]],
            res_id: channel.id,
            target: "current",
        });
    },
    icon: "settings",
    iconClass: "oi-filled",
    name: _t("Advanced Settings"),
    sequence: 20,
    sequenceGroup: 30,
});
