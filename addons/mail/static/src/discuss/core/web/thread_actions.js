/* @odoo-module */

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
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Discuss"),
    open(component) {
        component.threadService.setDiscussThread(component.thread);
        component.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
                name: _t("Discuss"),
            },
            { clearBreadcrumbs: true }
        );
    },
    setup() {
        const component = useComponent();
        component.actionService = useService("action");
        component.threadService = useService("mail.thread");
    },
    sequence: 15,
});
