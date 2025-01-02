import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

threadActionsRegistry.add("leave", {
    condition: (component) =>
        component.ui.isSmall && (component.thread?.canLeave || component.thread?.canUnpin),
    icon: "fa fa-fw fa-sign-out text-danger",
    name: (component) => (component.thread.canLeave ? _t("Leave") : _t("Unpin")),
    nameClass: "text-danger",
    open: (component) =>
        component.thread.canLeave ? component.thread.leaveChannel() : component.thread.unpin(),
    sequence: 10,
    sequenceGroup: 40,
    setup() {
        const component = useComponent();
        component.ui = useService("ui");
    },
});
