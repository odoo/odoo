/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

const { useState } = owl;

export class EditBar extends LegacyComponent {
    static template = "EditBar";

    setup() {
        super.setup();
        this.state = useState({ isColorPicker: false });
    }
}
