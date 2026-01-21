import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class SelectDefaultPrinterPopup extends Component {
    static template = "point_of_sale.SelectDefaultPrinterPopup";
    static components = { Dialog };
    static props = {
        receipt_printers: Array,
        close: Function,
        getPayload: Function,
        selectedId: { type: Number, optional: true },
        title: { type: String, optional: true },
        header: { type: String, optional: true },
        note: { type: String, optional: true },
    };
    static defaultProps = {
        title: _t("Several printers are available"),
        header: _t("Choose another printer"),
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
