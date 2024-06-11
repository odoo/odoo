/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

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
    sequence: 15,
});
