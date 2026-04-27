import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class ApplyQuantDialog extends Component {
    static components = { Dialog };
    static props = {
        onApply: Function,
        onApplyAll: Function,
        close: Function,
    };
    static template = "stock_barcode.ApplyQuantDialog";

    onApply() {
        this.props.onApply();
        this.props.close();
    }

    onApplyAll() {
        this.props.onApplyAll();
        this.props.close();
    }
}
