/** @odoo-module **/

import { registry } from "../registry";
import { useService } from "../service_hook";

const { Component, tags } = owl;

class ErrorHandler extends Component {
    catchError(error) {
        this.props.callback();
        throw error;
    }
}
ErrorHandler.template = tags.xml`<t t-component="props.dialog.class" t-props="props.dialog.props" />`;

export class DialogContainer extends Component {
    setup() {
        this.dialogs = {};
        const { bus } = useService("dialog");
        bus.on("ADD", this, (dialog) => {
            this.dialogs[dialog.id] = dialog;
            this.render();
        });
        bus.on("CLOSE", this, (id) => {
            this.closeDialog(id);
        });
    }

    onDialogClosed(id) {
        this.closeDialog(id);
    }

    closeDialog(id) {
        if (this.dialogs[id].options && this.dialogs[id].options.onCloseCallback) {
            this.dialogs[id].options.onCloseCallback();
        }
        delete this.dialogs[id];
        this.render();
    }

    errorCallBack(id) {
        return () => this.closeDialog(id);
    }

    __destroy() {
        this.env.bus.off("ADD", this);
        this.env.bus.off("CLOSE", this);
        super.__destroy();
    }
}
DialogContainer.components = { ErrorHandler };
DialogContainer.template = tags.xml`
    <div class="o_dialog_manager">
      <t t-foreach="Object.values(dialogs)" t-as="dialog" t-key="dialog.id">
        <ErrorHandler dialog="dialog" t-on-dialog-closed="onDialogClosed(dialog.id)" callback="errorCallBack(dialog.id)" />
      </t>
    </div>
    `;

registry.category("main_components").add("DialogContainer", {
    Component: DialogContainer,
});
