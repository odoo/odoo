import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class BackorderDialog extends Component {
    static components = { Dialog };
    static props = {
        displayUoM: Boolean,
        uncompletedLines: Array,
        onApply: Function,
        close: Function,
    };
    static template = "stock_barcode.BackorderDialog";

    async _onApply() {
        await this.props.onApply();
        this.props.close();
    }
}
