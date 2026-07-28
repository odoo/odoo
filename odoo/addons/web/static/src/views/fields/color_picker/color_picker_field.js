/** @odoo-module **/

import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class ColorPickerField extends Component {
    static template = "web.ColorPickerField";
    static components = {
        ColorList,
    };
    static props = {
        ...standardFieldProps,
        canToggle: { type: Boolean },
    };

    static RECORD_COLORS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];

    get isExpanded() {
        return !this.props.canToggle && !this.props.readonly;
    }

    switchColor(colorIndex) {
        this.props.record.update({ [this.props.name]: colorIndex });
    }
}

export const colorPickerField = {
    component: ColorPickerField,
    supportedTypes: ["integer"],
    extractProps: ({ viewType }) => ({
        canToggle: viewType !== "list",
    }),
};

registry.category("fields").add("color_picker", colorPickerField);
