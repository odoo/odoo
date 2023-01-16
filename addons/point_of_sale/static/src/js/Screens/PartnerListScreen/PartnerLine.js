/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class PartnerLine extends PosComponent {
    static template = "PartnerLine";

    get highlight() {
        return this._isPartnerSelected ? "highlight" : "";
    }
    get shortAddress() {
        const { partner } = this.props;
        return [partner.zip, partner.city, partner.state_id[1]].filter((field) => field).join(", ");
    }
    get _isPartnerSelected() {
        return this.props.partner === this.props.selectedPartner;
    }
}
