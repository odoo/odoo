import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CancelDialog extends Component {
    static template = "pos_glory_cash.CancelDialog";
    static components = { Dialog };
    static props = {
        message: String,
        cancel: Function,
        close: Function,
    };
}
