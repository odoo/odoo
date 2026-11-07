import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GloryErrorDialog extends Component {
    static template = "pos_glory_cash.GloryErrorDialog";
    static components = { Dialog };
    static props = {
        errorCode: { type: String, optional: true },
        errorGif: { type: String, optional: true },
        message: { type: String, optional: true },
        reset: { type: Function, optional: true },
        close: Function,
    };
}
