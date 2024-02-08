import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

threadActionsRegistry.add("expand-discuss", {
    condition(component) {
        return (
            component.thread &&
            component.props.chatWindow?.isOpen &&
            component.thread.model === "discuss.channel" &&
            !component.ui.isSmall
        );
    },
    setup() {
        const component = useComponent();
        component.actionService = useService("action");
    },
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Discuss"),
    shouldClearBreadcrumbs(component) {
        return false;
    },
    open(component) {
        component.thread.setAsDiscussThread();
        component.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            { clearBreadcrumbs: this.shouldClearBreadcrumbs(component) }
        );
    },
    sequence: 15,
});
