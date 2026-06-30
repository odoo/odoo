import { Component, proxy, props, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectDefaultPrinterPopup extends Component {
    static template = "point_of_sale.SelectDefaultPrinterPopup";
    static components = { Dialog };
    props = props({
        receipt_printers: t.array(),
        close: t.function(),
        getPayload: t.function(),
        selectedId: t.number().optional(),
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
