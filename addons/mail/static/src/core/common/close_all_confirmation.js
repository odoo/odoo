import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";

export class CloseAllConfirmation extends Component {
    static template = "mail.CloseAllConfirmation";
    static components = { Dialog };
    static props = {
        ...Dialog.props,
        message: String,
        close: Function,
        onConfirm: Function,
        slots: { optional: true },
    };

    onClickConfirm() {
        if (this.props.onConfirm) {
            this.props.onConfirm();
        }
        this.props.close();
    }
}
