/** @odoo-module **/

import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class ColorPickerField extends Component {
    get canToggle() {
        return true;
    }

    get isExpanded() {
        return !this.canToggle && !this.props.readonly;
    }

    switchColor(colorIndex) {
        this.props.update(colorIndex);
    }
}

export class ListColorPickerField extends Component {
    get canToggle() {
        return false;
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
registry.category("fields").add("list.color_picker", ColorPickerField);
