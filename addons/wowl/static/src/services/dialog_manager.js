/** @odoo-module **/

const { Component, core, tags, hooks } = owl;
const { EventBus } = core;
const { useState } = hooks;

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
    delete this.dialogs[id];
  }
}
DialogManager.template = tags.xml`
    <div class="o_dialog_manager">
      <t t-foreach="Object.values(dialogs)" t-as="dialog" t-key="dialog.id">
        <t t-component="dialog.class" t-props="dialog.props" t-on-dialog-closed="onDialogClosed(dialog.id)"/>
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
