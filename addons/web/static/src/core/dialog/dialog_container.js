/** @odoo-module **/

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
        this.props.bus.on("UPDATE", this, this.render);
    }

    close(id) {
        if (this.props.dialogs[id]) {
            this.props.dialogs[id].props.close();
        }
    }

    errorCallBack(id) {
        return () => this.close(id);
    }
}
DialogContainer.components = { ErrorHandler };
DialogContainer.template = tags.xml`
    <div class="o_dialog_container" t-att-class="{'modal-open': Object.keys(props.dialogs).length > 0}">
      <t t-foreach="Object.values(props.dialogs)" t-as="dialog" t-key="dialog.id">
        <ErrorHandler dialog="dialog" t-on-dialog-closed="dialog.props.close()" callback="errorCallBack(dialog.id)"
            t-att-class="{o_inactive_modal: !dialog_last}"/>
      </t>
    </div>
    `;
