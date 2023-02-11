/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useEffect } from "@web/core/utils/hooks";

const { hooks } = owl;

const LEGACY_SIZE_CLASSES = {
    "extra-large": "modal-xl",
    large: "modal-lg",
    small: "modal-sm",
};

// -----------------------------------------------------------------------------
// Action Dialog (Component)
// -----------------------------------------------------------------------------
class ActionDialog extends Dialog {
    setup() {
        super.setup();
        useOwnDebugContext();
        this.actionRef = hooks.useRef("actionRef");
        const actionProps = this.props && this.props.actionProps;
        const action = actionProps && actionProps.action;
        this.actionType = action && action.type;
        this.title = "title" in this.props ? this.props.title : this.constructor.title;
    }
}
ActionDialog.components = { ...Dialog.components, DebugMenu };
ActionDialog.template = "web.ActionDialog";
ActionDialog.bodyTemplate = "web.ActionDialogBody";
ActionDialog.props = {
    ActionComponent: { optional: true },
    actionProps: { optional: true },
    title: { optional: true },
    close: Function,
};

/**
 * This LegacyAdaptedActionDialog class will disappear when legacy code will be entirely rewritten.
 * The "ActionDialog" class should get exported from this file when the cleaning will occur.
 */
class LegacyAdaptedActionDialog extends ActionDialog {
    setup() {
        super.setup();
        const actionProps = this.props && this.props.actionProps;
        const action = actionProps && actionProps.action;
        const actionContext = action && action.context;
        const actionDialogSize = actionContext && actionContext.dialog_size;
        this.size = LEGACY_SIZE_CLASSES[actionDialogSize] || this.constructor.size;
        const ControllerComponent = this.props && this.props.ActionComponent;
        const Controller = ControllerComponent && ControllerComponent.Component;
        this.isLegacy = Controller && Controller.isLegacy;
        useEffect(
            () => {
                if (this.isLegacy) {
                    // Retrieve the widget climbing the wrappers
                    const componentController = this.actionRef.comp;
                    const controller = componentController.componentRef.comp;
                    const viewAdapter = controller.controllerRef.comp;
                    const widget = viewAdapter.widget;
                    // Render legacy footer buttons
                    const footer = this.modalRef.el.querySelector("footer");
                    widget.renderButtons($(footer));
                }
            },
            () => []
        ); // TODO: should this depend on actionRef.comp?
    }
}
LegacyAdaptedActionDialog.footerTemplate = "web.LegacyAdaptedActionDialogFooter";

export { LegacyAdaptedActionDialog as ActionDialog };
