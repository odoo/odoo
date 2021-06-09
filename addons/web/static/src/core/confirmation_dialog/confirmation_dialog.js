/** @odoo-module */

import { Dialog } from "../dialog/dialog";

export class ConfirmationDialog extends Dialog {
    setup() {
        super.setup();
        this.title = this.props.title;
    }
    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.close();
    }

    _confirm() {
        this.props.confirm();
        this.close();
    }
}
ConfirmationDialog.props = {
    title: String,
    body: String,
    confirm: Function,
    cancel: Function,
    close: Function,
};

ConfirmationDialog.bodyTemplate = "web.ConfirmationDialogBody";
ConfirmationDialog.footerTemplate = "web.ConfirmationDialogFooter";
