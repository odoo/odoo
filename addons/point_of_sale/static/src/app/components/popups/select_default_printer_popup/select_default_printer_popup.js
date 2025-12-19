import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectDefaultPrinterPopup extends Component {
    static template = "point_of_sale.SelectDefaultPrinterPopup";
    static components = { Dialog };
    static props = {
        receipt_printers: Array,
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.state = useState({
            selectedId: null,
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
