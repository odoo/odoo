/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class PSNumpadInputButton extends PosComponent {
    get _class() {
        return this.props.changeClassTo || "input-button number-char";
    }
}
PSNumpadInputButton.template = "PSNumpadInputButton";

Registries.Component.add(PSNumpadInputButton);

export default PSNumpadInputButton;
