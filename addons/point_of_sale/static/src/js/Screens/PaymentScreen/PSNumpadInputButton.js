/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class PSNumpadInputButton extends LegacyComponent {
    static template = "PSNumpadInputButton";

    get _class() {
        return this.props.changeClassTo || "input-button number-char";
    }
}
