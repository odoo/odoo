import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export const expandDiscussSequenceGroup = 5;
export const expandDiscussSequenceQuick = 0;

registerThreadAction("expand-discuss", {
    condition: ({ ancestors, channel, store }) =>
        user.isRegularUser &&
        channel &&
        ancestors.inChatWindow &&
        !store.ui.isSmall() &&
        !ancestors.inMessagingMenu,
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
    condition: ({ ancestors, channel }) =>
        ["channel", "group"].includes(channel?.channel_type) &&
        ["owner", "admin"].includes(channel.self_member_id?.channel_role) &&
        !ancestors.inDiscussContent,
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
registerThreadAction("view-recordings", {
    condition: ({ ancestors, channel }) => channel && !ancestors.inDiscussContent,
    async onSelected({ channel, store }) {
        const action = await store.orm.call("discuss.channel", "action_view_recordings", [
            [channel.id],
        ]);
        if (action) {
            await store.env.services.action.doAction(action);
        }
    },
    icon: "movie",
    name: _t("View Recordings"),
    sequence: 15,
    sequenceGroup: 30,
});
