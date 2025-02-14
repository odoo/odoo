import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class FailureDialog extends Component {
    static template = "pos_tyro.FailureDialog";
    static components = { Dialog };
    static props = {
        result: String,
        hasReceipt: Boolean,
        printReceipt: Function,
        close: Function,
    };
}
