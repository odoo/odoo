/** @odoo-module */

import { Component, useExternalListener } from "@odoo/owl";

export class EditBar extends Component {
    static template = "pos_restaurant.EditBar";
    static props = {
        selectedTables: Object,
        nbrFloors: Number,
        floorMapScrollTop: Number,
        isColorPicker: Boolean,
        toggleColorPicker: Function,
        createTable: Function,
        duplicateTableOrFloor: Function,
        renameTable: Function,
        changeSeatsNum: Function,
        changeToCircle: Function,
        changeToSquare: Function,
        setTableColor: Function,
        setFloorColor: Function,
        deleteFloorOrTable: Function,
        toggleEditMode: Function,
    };

    setup() {
        super.setup();
        useExternalListener(window, "click", this.onOutsideClick);
    }

    onOutsideClick() {
        if (this.props.isColorPicker) {
            this.props.isColorPicker = false;
        }
    }

    getSelectedTablesShape() {
        let shape = 'round';
        this.props.selectedTables.forEach((table) => {
            if (table.shape == 'square') {
                shape = 'square';
            }
        });
        return shape; 
    }
}
