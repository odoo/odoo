import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

registerThreadAction("expand-discuss", {
    condition(component) {
        return (
            component.thread &&
            component.props.chatWindow?.isOpen &&
            component.thread.model === "discuss.channel" &&
            !component.ui.isSmall
        );
    },
    setup(component) {
        component.actionService = useService("action");
    },
    icon: "fa fa-fw fa-expand",
    iconLarge: "fa fa-lg fa-fw fa-expand",
    name: _t("Open in Discuss"),
    shouldClearBreadcrumbs(component) {
        return false;
    },
    open(component) {
        component.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            {
                clearBreadcrumbs: this.shouldClearBreadcrumbs(component),
                additionalContext: { active_id: component.thread.id },
            }
        );
    },
    sequence: 10,
    sequenceGroup: 5,
});
registerThreadAction("advanced-settings", {
    condition: (component) => component.thread,
    open(component, action) {
        action.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "discuss.channel",
            views: [[false, "form"]],
            res_id: component.thread.id,
            target: "current",
        });
    },
    icon: "fa fa-fw fa-gear",
    iconLarge: "fa fa-lg fa-fw fa-gear",
    name: _t("Advanced Settings"),
    partition: false,
    setup() {
        this.actionService = useService("action");
    },
    sidebarSequence: 20,
    sidebarSequenceGroup: 30,
});
