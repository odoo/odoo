import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// Kept in /odoo web client because action service is only present there
threadActionsRegistry.add("expand-form", {
    condition(component) {
        return (
            component.thread &&
            !["mail.box", "discuss.channel"].includes(component.thread.model) &&
            component.props.chatWindow?.isOpen
        );
    },
    setup() {
        const component = useComponent();
        component.actionService = useService("action");
    },
    icon: "fa fa-fw fa-expand",
    iconLarge: "fa fa-lg fa-fw fa-expand",
    name: _t("Open Form View"),
    open(component) {
        component.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: component.thread.id,
            res_model: component.thread.model,
            views: [[false, "form"]],
        });
        component.props.chatWindow.close();
    },
    sequence: 40,
    sequenceGroup: 20,
});
