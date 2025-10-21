import { ThreadAction, threadActionsRegistry } from "@mail/core/common/thread_actions";
import { patch } from "@web/core/utils/patch";

patch(ThreadAction.prototype, {
    _condition({ action, channel, store }) {
        const visitorActions = [
            "fold-chat-window",
            "close",
            "restart",
            "call-settings",
            "meeting-chat",
        ];
        if (
            channel?.channel_type === "livechat" &&
            !store.self_user &&
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
