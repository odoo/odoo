import { Component, props, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CancelDialog extends Component {
    static template = "pos_glory_cash.CancelDialog";
    static components = { Dialog };
    props = props({
        message: t.string(),
        cancel: t.function(),
        close: t.function(),
    });
}
