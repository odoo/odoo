/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class PartnerLine extends PosComponent {
    get highlight() {
        return this._isPartnerSelected ? "highlight" : "";
    }
    get _isPartnerSelected() {
        return this.props.partner === this.props.selectedPartner;
    }
}
PartnerLine.template = "PartnerLine";

Registries.Component.add(PartnerLine);

export default PartnerLine;
