/** @odoo-module **/

import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class ColorPickerField extends Component {
    get canToggle() {
        return this.props.record.activeFields[this.props.name].viewType !== "list";
    }

    get isExpanded() {
        return !this.canToggle && !this.props.readonly;
    }

    switchColor(colorIndex) {
        this.props.update(colorIndex);
    }
}

ColorPickerField.template = "web.ColorPickerField";
ColorPickerField.components = {
    ColorList,
};
ColorPickerField.props = {
    ...standardFieldProps,
};

ColorPickerField.supportedTypes = ["integer"];
ColorPickerField.RECORD_COLORS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];

registry.category("fields").add("color_picker", ColorPickerField);
