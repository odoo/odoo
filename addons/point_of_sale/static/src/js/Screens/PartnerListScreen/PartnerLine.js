/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class PartnerLine extends PosComponent {
    static template = "PartnerLine";

    get highlight() {
        return this._isPartnerSelected ? "highlight" : "";
    }
    get _isPartnerSelected() {
        return this.props.partner === this.props.selectedPartner;
    }
}
