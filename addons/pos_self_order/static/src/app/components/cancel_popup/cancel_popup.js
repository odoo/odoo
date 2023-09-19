/** @odoo-module */

import { Component } from "@odoo/owl";

export class CancelPopup extends Component {
    static template = "pos_self_order.CancelPopup";

    confirm() {
        this.props.close();
        this.props.confirm();
    }
}
