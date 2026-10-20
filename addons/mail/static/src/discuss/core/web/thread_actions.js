import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

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
registerThreadAction("view-recordings", {
    condition: ({ channel, owner }) => channel && !owner.isDiscussContent,
    async onSelected({ channel, store }) {
        const action = await store.env.services.orm.call(
            "discuss.channel",
            "action_view_recordings",
            [[channel.id]]
        );
        if (action) {
            await store.env.services.action.doAction(action);
        }
    },
    icon: "movie",
    name: _t("View Recordings"),
    sequence: 15,
    sequenceGroup: 30,
});
