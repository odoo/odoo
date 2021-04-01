/** @odoo-module **/

import { ActionDialog } from "./action_dialog";
import { setScrollPosition } from "./action_hook";

const { Component, tags } = owl;

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
  setup() {
    this.main = {};
    this.dialog = {};
    this.env.bus.on("ACTION_MANAGER:UPDATE", this, (info) => {
      switch (info.type) {
        case "MAIN":
          this.main = info;
          break;
        case "OPEN_DIALOG": {
          const { onClose } = this.dialog;
          this.dialog = {
            id: info.id,
            props: info.props,
            onClose: onClose || info.onClose,
          };
          break;
        }
        case "CLOSE_DIALOG": {
          let onClose;
          if (this.dialog.id) {
            onClose = this.dialog.onClose;
          } else {
            onClose = info.onClose;
          }
          if (onClose) {
            onClose(info.onCloseInfo);
          }
          this.dialog = {};
          break;
        }
      }
      this.render();
    });
  }

  onDialogClosed() {
    this.dialog = {};
    this.render();
  }
}
ActionContainer.components = { ActionDialog };
ActionContainer.template = tags.xml`
    <div t-name="wowl.ActionContainer" class="o_action_manager">
      <t t-if="main.Component" t-component="main.Component" t-props="main.componentProps" t-key="main.id"/>
      <ActionDialog t-if="dialog.id" t-props="dialog.props" t-key="dialog.id" t-on-dialog-closed="onDialogClosed"/>
    </div>`;
