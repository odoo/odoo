/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

import { ColorList } from "@web/core/colorlist/colorlist";

const { Component } = owl;

export class ColorPickerField extends Component {
    get isReadonly() {
        return this.props.record.activeFields[this.props.name].modifiers.readonly;
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
