import { ThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ThreadAction.prototype, {
    _condition({ action, channel, store }) {
        const visitorActions = [
            "fold-chat-window",
            "close",
            "restart",
            "call-settings",
            "meeting-chat",
            "leave",
            "notification-settings",
        ];
        if (
            channel?.channel_type === "livechat" &&
            store.self_user?.share !== false &&
            !visitorActions.includes(action.id)
        ) {
            return false;
        }
        return super._condition(...arguments);
    },
});

patch(threadActionsRegistry.get("invite-people"), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("notification-settings"), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("camera-call"), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("call"), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("leave"), {
    name(args) {
        const { channel } = args;
        if (
            channel?.channel_type === "livechat" &&
            !channel.channel_member_ids.some(
                (m) => m.livechat_member_type === "agent" && m.notEq(channel.self_member_id)
            )
        ) {
            return _t("Close Conversation");
        }
        return _t("Leave Channel");
    },
});
