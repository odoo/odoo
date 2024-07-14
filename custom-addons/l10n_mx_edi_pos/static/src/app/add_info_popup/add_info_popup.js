/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState } from "@odoo/owl";

export class AddInfoPopup extends AbstractAwaitablePopup {
    static template = "l10n_mx_edi_pos.AddInfoPopup"

    setup() {
        super.setup();
        this.pos = usePos();
        const order = this.props.order;
        const partner = order.get_partner()
        // when opening the popup for the first time, both variables are undefined !
        this.state = useState({
            l10n_mx_edi_usage: partner?.l10n_mx_edi_usage || order.l10n_mx_edi_usage || 'G01',
            l10n_mx_edi_cfdi_to_public: !!order.l10n_mx_edi_cfdi_to_public,
        });
    }

    async getPayload() {
        return this.state;
    }
}
