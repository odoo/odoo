import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GloryErrorDialog extends Component {
    static template = "pos_glory_cash.GloryErrorDialog";
    static components = { Dialog };
    static props = {
        errorCode: String,
        errorGif: String,
        reset: Function,
        close: Function,
    };
}
