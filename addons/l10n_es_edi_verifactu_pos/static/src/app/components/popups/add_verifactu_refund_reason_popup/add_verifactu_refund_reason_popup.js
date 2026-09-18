import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { Component, proxy, t, useProps } from "@odoo/owl";

export class AddVerifactuRefundReasonPopup extends Component {
    static template = "l10n_es_edi_verifactu_pos.AddVerifactuRefundReasonPopup";
    static components = { Dialog };

    props = useProps({
        close: t.function(),
        getPayload: t.function(),
        order: t.instanceOf(PosOrder),
    });

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
