import { Component, proxy, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

export class AddZatcaRefundReasonPopup extends Component {
    static template = "l10n_sa_pos.AddZatcaRefundReasonPopup";
    static components = { Dialog };

    props = useProps({
        close: t.function(),
        getPayload: t.function(),
        order: t.instanceOf(PosOrder),
    });

    setup() {
        this.pos = usePos();
        this.state = proxy({
            l10n_sa_reason: this.props.order.l10n_sa_reason || "BR-KSA-17-reason-4",
        });
    }
    confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
