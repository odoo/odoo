/** @odoo-module */

import { Dialog } from "../dialog/dialog";
import { _lt } from "../l10n/translation";

const { Component } = owl;

export class ConfirmationDialog extends Component {
    setup() {
        this.env.dialogData.close = () => this._cancel();
    }
    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }

    _confirm() {
        if (this.props.confirm) {
            this.props.confirm();
        }
        this.props.close();
    }
}
ConfirmationDialog.template = "web.ConfirmationDialog";
ConfirmationDialog.components = { Dialog };
ConfirmationDialog.props = {
    close: Function,
    title: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
        optional: true,
    },
    body: String,
    confirm: { type: Function, optional: true },
    confirmLabel: { type: String, optional: true },
    cancel: { type: Function, optional: true },
    cancelLabel: { type: String, optional: true },
};
ConfirmationDialog.defaultProps = {
    confirmLabel: _lt("Ok"),
    cancelLabel: _lt("Cancel"),
    title: _lt("Confirmation"),
};

export class AlertDialog extends ConfirmationDialog {}
AlertDialog.template = "web.AlertDialog";
AlertDialog.props = {
    ...ConfirmationDialog.props,
    contentClass: { type: String, optional: true },
};
AlertDialog.defaultProps = {
    title: _lt("Alert"),
};
