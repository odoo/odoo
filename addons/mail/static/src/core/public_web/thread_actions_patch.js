import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";

threadActionsRegistry.add("leave", {
    condition: (component) =>
        component.ui.isSmall && (component.thread?.canLeave || component.thread?.canUnpin),
    icon: "fa fa-fw fa-sign-out text-danger",
    name: (component) => (component.thread.canLeave ? _t("Leave") : _t("Unpin")),
    open: (component) =>
        component.thread.canLeave ? component.thread.leaveChannel() : component.thread.unpin(),
    sequence: 100,
});
