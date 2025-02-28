import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { patch } from "@web/core/utils/patch";

patch(threadActionsRegistry.get("invite-people"), {
    condition(component) {
        return (
            component.thread?.model === "discuss.channel" &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen) &&
            !component.thread?.composerDisabled
        );
    },
});

patch(threadActionsRegistry.get("notification-settings"), {
    condition(component) {
        return (
            component.thread?.model === "discuss.channel" &&
            component.store.self.type !== "guest" &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen) &&
            !component.thread?.composerDisabled
        );
    },
});

patch(threadActionsRegistry.get("camera-call"), {
    condition(component) {
        return (
            component.thread?.allowCalls &&
            !component.thread?.eq(component.rtc.state.channel) &&
            !component.thread?.composerDisabled
        );
    },
});

patch(threadActionsRegistry.get("call"), {
    condition(component) {
        return (
            component.thread?.allowCalls &&
            !component.thread?.eq(component.rtc.state.channel) &&
            !component.thread?.composerDisabled
        );
    },
});
