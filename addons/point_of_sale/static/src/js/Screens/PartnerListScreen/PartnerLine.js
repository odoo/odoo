/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class PartnerLine extends LegacyComponent {
    static template = "PartnerLine";

    get highlight() {
        return this._isPartnerSelected ? "highlight" : "";
    }
    get _isPartnerSelected() {
        return this.props.partner === this.props.selectedPartner;
    }
}
