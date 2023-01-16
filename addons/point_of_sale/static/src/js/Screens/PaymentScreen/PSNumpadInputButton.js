/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class PSNumpadInputButton extends PosComponent {
    static template = "PSNumpadInputButton";

    get _class() {
        return this.props.changeClassTo || "input-button number-char";
    }
}
