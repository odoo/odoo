/** @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PSNumpadInputButton extends Component {
    static template = "PSNumpadInputButton";

    setup() {
        this.numberBuffer = useService("number_buffer");
    }

    get _class() {
        return this.props.changeClassTo || "input-button number-char";
    }
}
