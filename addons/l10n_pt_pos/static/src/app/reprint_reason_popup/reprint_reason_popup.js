import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";

export class ReprintReasonPopup extends Component {
    static template = "l10n_pt_pos.ReprintReasonPopup";
    static components = { Dialog };
    static props = {
        order: Object,
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            reprint_reason: "",
        });
    }
    confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }
}
