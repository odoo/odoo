import { registerThreadAction } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

registerThreadAction("leave", {
    condition: (component) => component.thread?.canLeave || component.thread?.canUnpin,
    danger: true,
    icon: "fa fa-fw fa-sign-out",
    iconLarge: "fa fa-fw fa-lg fa-sign-out",
    name: (component) =>
        component.thread.canLeave ? _t("Leave Channel") : _t("Unpin Conversation"),
    open: (component) =>
        component.thread.canLeave ? component.thread.leaveChannel() : component.thread.unpin(),
    partition: (component) => component.env.inChatWindow,
    sequence: 10,
    sequenceGroup: 40,
    setup(component) {
        component.ui = useService("ui");
    },
    sidebarSequence: 10,
    sidebarSequenceGroup: 40,
});
