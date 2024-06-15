/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TransferMergeDialog extends Component {
    static template = "pos_restaurant.TransferMergeDialog";
    static components = { Dialog };
    static props = {
        isTableToMerge: false,
        title: String,
        close: Function,
        getPayload: Function,
    };
    closeDialog() {
        this.props.close();
    }
    confirm(merge) {
        if (merge) {
            this.props.getPayload(true);
        } else {
            this.props.getPayload(false);
        }
        this.props.close();
    }
}
