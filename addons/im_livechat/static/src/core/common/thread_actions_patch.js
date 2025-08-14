import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { patch } from "@web/core/utils/patch";

patch(threadActionsRegistry.get("invite-people"), {
    condition({ thread }) {
        if (thread?.channel_type === "livechat") {
            return super.condition(...arguments) && !thread.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("notification-settings"), {
    condition({ thread }) {
        if (thread?.channel_type === "livechat") {
            return super.condition(...arguments) && !thread.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("camera-call"), {
    condition({ thread }) {
        if (thread?.channel_type === "livechat") {
            return super.condition(...arguments) && !thread.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get("call"), {
    condition({ thread }) {
        if (thread?.channel_type === "livechat") {
            return super.condition(...arguments) && !thread.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});
