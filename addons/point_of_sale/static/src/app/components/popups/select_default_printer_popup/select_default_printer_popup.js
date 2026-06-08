import { Component, proxy, props, types } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectDefaultPrinterPopup extends Component {
    static template = "point_of_sale.SelectDefaultPrinterPopup";
    static components = { Dialog };
    props = props({
        receipt_printers: types.array(),
        close: types.function(),
        getPayload: types.function(),
        "selectedId?": types.number(),
    });
    setup() {
        this.state = proxy({
            selectedId: this.props.selectedId,
        });
    }

    confirmSelection() {
        if (!this.state.selectedId) {
            return;
        }
        this.props.getPayload(this.state.selectedId);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
