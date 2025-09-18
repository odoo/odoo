import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dialog } from "@web/ui/dialog/dialog";
export class AddZatcaRefundReasonPopup extends Component {
    static template = "l10n_sa_pos.AddZatcaRefundReasonPopup";
    static components = { Dialog };

    setup() {
        this.pos = usePos();
        this.state = useState({
            l10n_sa_reason: this.props.order.l10n_sa_reason || "BR-KSA-17-reason-4",
        });
    }
    confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
