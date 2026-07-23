import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CancelDialog extends Component {
    static template = "pos_glory_cash.CancelDialog";
    static components = { Dialog };
    props = useProps({
        message: t.string(),
        cancel: t.function(),
        close: t.function(),
    });
}
