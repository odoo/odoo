/** @odoo-module */

import { Component } from "@odoo/owl";

export class PartnerLine extends Component {
    static template = "PartnerLine";
    static props = {
        partner: Object,
        selectedPartner: "object",
        detailIsShown: Boolean,
        isBalanceDisplayed: Boolean,
        onClickEdit: Function,
        onClickPartner: Function,
    };

    get highlight() {
        return this._isPartnerSelected ? "highlight" : "";
    }
    get _isPartnerSelected() {
        return this.props.partner === this.props.selectedPartner;
    }
}
