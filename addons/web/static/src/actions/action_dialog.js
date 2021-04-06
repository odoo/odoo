/** @odoo-module **/
import { Dialog } from "../components/dialog/dialog";
import { DebugManager } from "../debug/debug_manager";

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
    this.actionRef = hooks.useRef("actionRef");
    const actionProps = this.props && this.props.actionProps;
    const action = actionProps && actionProps.action;
    this.actionType = action && action.type;
  }
}
ActionDialog.components = { ...Dialog.components, DebugManager };
ActionDialog.template = "web.ActionDialog";
ActionDialog.props = {
  ...Dialog.props,
  ActionComponent: { optional: true },
  actionProps: { optional: true },
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
    this.props.size = LEGACY_SIZE_CLASSES[actionDialogSize] || (this.props && this.props.size);
    const ControllerComponent = this.props && this.props.ActionComponent;
    const Controller = ControllerComponent && ControllerComponent.Component;
    this.isLegacy = Controller && Controller.isLegacy;
    hooks.onMounted(() => {
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
    });
  }
}
LegacyAdaptedActionDialog.template = "web.LegacyAdaptedActionDialog";

export { LegacyAdaptedActionDialog as ActionDialog };
