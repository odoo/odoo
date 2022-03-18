/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useLegacyRefs } from "@web/legacy/utils";

const { useEffect } = owl;

const LEGACY_SIZE_CLASSES = {
    "extra-large": "xl",
    large: "lg",
    medium: "md",
    small: "sm",
};

// -----------------------------------------------------------------------------
// Action Dialog (Component)
// -----------------------------------------------------------------------------
class ActionDialog extends Dialog {
    setup() {
        super.setup();
        useOwnDebugContext();
    }
}
ActionDialog.components = { ...Dialog.components, DebugMenu };
ActionDialog.template = "web.ActionDialog";
ActionDialog.props = {
    ...Dialog.props,
    close: Function,
    slots: { optional: true },
    ActionComponent: { optional: true },
    actionProps: { optional: true },
    actionType: { optional: true },
    title: { optional: true },
};

/**
 * This LegacyAdaptedActionDialog class will disappear when legacy code will be entirely rewritten.
 * The "ActionDialog" class should get exported from this file when the cleaning will occur, and it
 * should stop extending Dialog and use it normally instead at that point.
 */
class LegacyAdaptedActionDialog extends ActionDialog {
    setup() {
        super.setup();
        const actionProps = this.props && this.props.actionProps;
        const action = actionProps && actionProps.action;
        const actionContext = action && action.context;
        const actionDialogSize = actionContext && actionContext.dialog_size;
        this.props.size = LEGACY_SIZE_CLASSES[actionDialogSize] || Dialog.defaultProps.size;
        const ControllerComponent = this.props && this.props.ActionComponent;
        const Controller = ControllerComponent && ControllerComponent.Component;
        this.isLegacy = Controller && Controller.isLegacy;
        const legacyRefs = useLegacyRefs();
        useEffect(
            () => {
                if (this.isLegacy) {
                    // Render legacy footer buttons
                    const footer = this.modalRef.el.querySelector("footer");
                    legacyRefs.widget.renderButtons($(footer));
                }
            },
            () => []
        );
    }
}
LegacyAdaptedActionDialog.template = "web.LegacyAdaptedActionDialog";

export { LegacyAdaptedActionDialog as ActionDialog };
