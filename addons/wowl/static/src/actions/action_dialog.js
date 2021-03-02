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

/**
 * TrueActionDialog is the "true" ActionDialog class.
 * You should add new web client code in this TrueActionDialog class.
 * If you need to add legacy compatibility layer stuffs, please add them to
 * the ActionDialog exported class (see below).
 */
class TrueActionDialog extends Dialog {
  constructor(parent, props) {
    super(...arguments);
    this.actionRef = hooks.useRef("actionRef");
    const actionProps = props && props.actionProps;
    const action = actionProps && actionProps.action;
    this.actionType = action && action.type;
  }
}
TrueActionDialog.components = { ...Dialog.components, DebugManager };
TrueActionDialog.template = "wowl.TrueActionDialog";
TrueActionDialog.props = {
  ...Dialog.props,
  ActionComponent: { optional: true },
  actionProps: { optional: true },
};

/**
 * This ActionDialog class will disappear when legacy code will be entirely rewritten.
 * The "TrueActionDialog" class will get renamed to "ActionDialog"
 * and exported from this file when the cleaning will occur.
 */
export class ActionDialog extends TrueActionDialog {
  constructor(parent, props) {
    super(...arguments);
    const actionProps = props && props.actionProps;
    const action = actionProps && actionProps.action;
    const actionContext = action && action.context;
    const actionDialogSize = actionContext && actionContext.dialog_size;
    this.props.size = LEGACY_SIZE_CLASSES[actionDialogSize] || (props && props.size);
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
ActionDialog.template = "wowl.ActionDialog";
