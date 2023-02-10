/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class EditBar extends Component {
    static template = "pos_restaurant.EditBar";
    static props = {
        selectedTable: [{ type: Object, shape: { shape: String, "*": true } }, { value: false }],
        floorMapScrollTop: Number,
        createTable: Function,
        duplicateTable: Function,
        renameTable: Function,
        changeSeatsNum: Function,
        changeShape: Function,
        setTableColor: Function,
        setFloorColor: Function,
        deleteTable: Function,
    };

    setup() {
        super.setup();
        this.state = useState({ isColorPicker: false });
    }
}
