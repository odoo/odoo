import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, proxy } from "@odoo/owl";

export class AddVerifactuRefundReasonPopup extends Component {
    static template = "l10n_es_edi_verifactu_pos.AddVerifactuRefundReasonPopup";
    static components = { Dialog };

    setup() {
        this.pos = usePos();
        this.state = proxy({
            l10n_es_invoice_type: this.props.order.l10n_es_invoice_type || "R4",
        });
    }
    confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
