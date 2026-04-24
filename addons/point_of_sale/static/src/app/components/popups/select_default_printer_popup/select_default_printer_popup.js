import { useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectDefaultPrinterPopup extends Component {
    static template = "point_of_sale.SelectDefaultPrinterPopup";
    static components = { Dialog };
    static props = {
        receipt_printers: Array,
        close: Function,
        getPayload: Function,
        selectedId: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({
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
