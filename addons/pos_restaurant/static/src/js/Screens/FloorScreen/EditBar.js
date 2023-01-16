/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

const { useState } = owl;

export class EditBar extends PosComponent {
    static template = "EditBar";

    setup() {
        super.setup();
        this.state = useState({ isColorPicker: false });
    }
}
