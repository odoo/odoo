/** @odoo-module */

export class ConfirmationDialog extends owl.Component {
    _close() {
        this.trigger("dialog-closed");
    }

    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this._close();
    }

    _confirm() {
        this.props.confirm();
        this._close();
    }

    get dialogProps() {
        const propsArray = Object.entries(this.props).filter(
            ([k, v]) => !(k in this.constructor.props)
        );

        const props = {};
        propsArray.forEach(([k, v]) => {
            props[k] = v;
        });
        return props;
    }
}
ConfirmationDialog.props = {
    confirm: Function,
    cancel: Function,
};

ConfirmationDialog.template = "web.ConfirmationDialog";
