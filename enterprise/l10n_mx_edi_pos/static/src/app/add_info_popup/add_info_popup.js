import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";

export class AddInfoPopup extends Component {
    static template = "l10n_mx_edi_pos.AddInfoPopup";
    static components = { Dialog };
    static props = {
        order: Object,
        getPayload: Function,
        close: Function,
        newPartner: { optional: true },
    };

    setup() {
        this.pos = usePos();
        const order = this.props.order;
        const partner = order.get_partner() || this.props.newPartner;
        // when opening the popup for the first time, both variables are undefined !
        this.state = useState({
            l10n_mx_edi_usage: partner?.l10n_mx_edi_usage || order.l10n_mx_edi_usage || "G01",
            l10n_mx_edi_cfdi_to_public: !!order.l10n_mx_edi_cfdi_to_public,
        });
    }
    confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
