/** @odoo-module */

import { Component, useExternalListener, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";

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
        this.ui = useState(useService("ui"));
        useExternalListener(window, "click", this.onOutsideClick);
        this.doCreateTable = useTrackedAsync(this.props.createTable);
    }

    onOutsideClick() {
        if (this.props.isColorPicker) {
            this.props.isColorPicker = false;
        }
    }

    getSelectedTablesShape() {
        let shape = "round";
        this.props.selectedTables.forEach((table) => {
            if (table.shape == "square") {
                shape = "square";
            }
        });
        return shape;
    }
}
