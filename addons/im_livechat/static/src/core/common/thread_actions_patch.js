import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { patch } from "@web/core/utils/patch";

patch(threadActionsRegistry.get("invite-people"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && component.thread.livechat_active;
        }
        return super.condition(component);
    },
});

patch(threadActionsRegistry.get("notification-settings"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && component.thread.livechat_active;
        }
        return super.condition(component);
    },
});

patch(threadActionsRegistry.get("camera-call"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && component.thread.livechat_active;
        }
        return super.condition(component);
    },
});

patch(threadActionsRegistry.get("call"), {
    condition(component) {
        if (component.thread?.channel_type === "livechat") {
            return super.condition(component) && component.thread.livechat_active;
        }
        return super.condition(component);
    },
});
