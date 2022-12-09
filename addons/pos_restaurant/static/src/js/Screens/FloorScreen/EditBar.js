/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

const { useState } = owl;

class EditBar extends PosComponent {
    setup() {
        super.setup();
        this.state = useState({ isColorPicker: false });
    }
}
EditBar.template = "EditBar";

Registries.Component.add(EditBar);

export default EditBar;
