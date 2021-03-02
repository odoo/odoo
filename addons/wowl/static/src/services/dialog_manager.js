/** @odoo-module **/

import { serviceRegistry } from "./service_registry";

const { Component, core, tags, hooks } = owl;
const { EventBus } = core;
const { useState } = hooks;

class ErrorHandler extends Component {
    catchError(error) {
      this.props.callback();
      throw error;
  }
}
ErrorHandler.template = tags.xml`<t t-component="props.dialog.class" t-props="props.dialog.props" />`;

class DialogManager extends Component {
  constructor() {
    super(...arguments);
    this.dialogs = useState({});
    this.dialogId = 1;
  }

  addDialog(dialogClass, props) {
    const id = this.dialogId++;
    this.dialogs[id] = {
      id,
      class: dialogClass,
      props,
    };
  }

  onDialogClosed(id) {
    this._doCloseDialog(id);
  }

  _doCloseDialog(id) {
    delete this.dialogs[id];
  }

  _errorCallBack(id) {
    return () => this._doCloseDialog(id);
  }
}
DialogManager.components = { ErrorHandler };
DialogManager.template = tags.xml`
    <div class="o_dialog_manager">
      <t t-foreach="Object.values(dialogs)" t-as="dialog" t-key="dialog.id">
        <ErrorHandler dialog="dialog" t-on-dialog-closed="onDialogClosed(dialog.id)" callback="_errorCallBack(dialog.id)" />
      </t>
    </div>
    `;

export const dialogManagerService = {
  name: "dialog_manager",
  deploy(env) {
    const bus = new EventBus();
    class ReactiveDialogManager extends DialogManager {
      constructor() {
        super(...arguments);
        bus.on("UPDATE", this, (dialogClass, props) => {
          this.addDialog(dialogClass, props);
        });
      }
    }
    odoo.mainComponentRegistry.add("DialogManager", ReactiveDialogManager);
    function open(dialogClass, props) {
      bus.trigger("UPDATE", dialogClass, props);
    }
    return { open };
  },
};

serviceRegistry.add("dialog_manager", dialogManagerService);