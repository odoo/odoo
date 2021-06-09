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
        this.props.bus.on("ADD", this, this.add);
        this.props.bus.on("REMOVE", this, this.remove);
    }
    __destroy() {
        this.props.bus.off("ADD", this);
        this.props.bus.off("REMOVE", this);
        super.__destroy();
    }

    add(params) {
        this.dialogs[params.id] = params;
        this.render();
    }
    remove(id) {
        if (this.dialogs[id]) {
            delete this.dialogs[id];
            this.render();
        }
    }

    onDialogClosed(id) {
        this.remove(id);
    }
    errorCallBack(id) {
        return () => this.remove(id);
    }
}
DialogContainer.components = { ErrorHandler };
DialogContainer.template = tags.xml`
    <div class="o_dialog_container" t-att-class="{'modal-open': Object.keys(dialogs).length > 0}">
      <t t-foreach="Object.values(dialogs)" t-as="dialog" t-key="dialog.id">
        <ErrorHandler dialog="dialog" t-on-dialog-closed="onDialogClosed(dialog.id)" callback="errorCallBack(dialog.id)"
            t-att-class="{o_inactive_modal: !dialog_last}"/>
      </t>
    </div>
    `;
