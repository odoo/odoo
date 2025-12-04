import { Component, useEffect } from "@odoo/owl";
import { Handles } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/handles/handles";
import { getColors } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import { useService } from "@web/core/utils/hooks";
import { SHAPE_TYPES } from "@pos_restaurant/app/services/floor_plan/elements/floor_element";

export class EditTableProperties extends Component {
    static template = "pos_restaurant.floor_editor.edit_table_properties";
    static components = { Handles };
    static props = {
        table: { optional: false },
        updateElement: Function,
        onSizeUpdated: Function,
    };

    setup() {
        this.dialog = useService("dialog");

        useEffect(
            (table) => {
                this.roundedCornerInitialValue = table.roundedCorner || 0;
            },
            () => [this.props.table]
        );
    }

    get table() {
        return this.props.table;
    }

    incrNumberOfSeats(value) {
        const newNumber = this.table.seats + value;
        if (newNumber >= 0) {
            this.updateTable({ seats: newNumber });
        }
    }

    updateTable(values) {
        this.props.updateElement(this.table.uuid, values);
    }

    updateTableNumber(event) {
        const target = event.target;
        this.saveTableNumber(target.value);
    }

    saveTableNumber(value) {
        const newNumber = parseInt(value);
        if (isNaN(newNumber)) {
            return;
        }
        this.updateTable({ table_number: newNumber });
    }

    getTableColors() {
        return getColors();
    }

    selectTableColor(color) {
        this.updateTable({ color: color });
    }

    defaultTableColor() {
        return this.table?.color;
    }

    changeTableShape(shape) {
        const { width, height } = this.table;
        const newSize = { width, height };

        if (shape === SHAPE_TYPES.SQUARE || shape === SHAPE_TYPES.CIRCLE) {
            const size = Math.min(width, height);
            newSize.width = size;
            newSize.height = size;
        } else if (width === height) {
            newSize.width = width * 1.5;
            newSize.height = height;
        }

        this.updateTable({
            width: newSize.width,
            height: newSize.height,
            shape: shape,
            left: this.table.left + (width - newSize.width) / 2,
            top: this.table.top + (height - newSize.height) / 2,
        });
    }

    updateRoundedCornerValue(event) {
        // Update visual appearance immediately without history
        this.table.roundedCorner = event.target.value;
    }

    commitRoundedCornerValue(event) {
        this.table.roundedCorner = this.roundedCornerInitialValue || 0; // Force history update
        this.updateTable({
            roundedCorner: event.target.value,
        });
    }
}
