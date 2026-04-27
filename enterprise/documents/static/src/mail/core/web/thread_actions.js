/**
 * Replace the expand form action with open document action to not open documents in form view.
 */
import { getDocumentActionRequest } from "@documents/utils";
import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { useComponent } from "@odoo/owl";

// Make sure the web actions are loaded before overriding them.
import "@mail/core/web/thread_actions";

const defaultCondition = threadActionsRegistry.get("expand-form").condition;

threadActionsRegistry.get("expand-form").condition = (component) =>
    defaultCondition(component) && component.thread.model !== "documents.document";

threadActionsRegistry.add("open-document", {
    condition(component) {
        return defaultCondition(component) && component.thread.model === "documents.document";
    },
    setup() {
        const component = useComponent();
        component.actionService = useService("action");
    },
    icon: "fa fa-fw fa-expand",
    name: _t("Open in Documents"),
    open(component) {
        component.actionService.doAction(getDocumentActionRequest(component.thread.id));
        component.props.chatWindow.close();
    },
    sequence: 40,
    sequenceGroup: 20,
});
