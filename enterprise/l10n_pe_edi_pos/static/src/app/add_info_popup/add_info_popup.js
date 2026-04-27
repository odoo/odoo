/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";

export class AddInfoPopup extends Component {
    static template = "l10n_pe_edi_pos.AddInfoPopup";
    static components = { Dialog };

    setup() {
        this.pos = usePos();
        this.state = useState({
            l10n_pe_edi_refund_reason: this.props.order.l10n_pe_edi_refund_reason || "01",
        });
    }

    async confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
