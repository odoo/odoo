// @ts-check

/** @module @web/fields/specialized/color_picker/color_picker_field - Predefined color palette picker field for Integer columns */

import { Component } from "@odoo/owl";
import { ColorList } from "@web/components/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";

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

    /** @returns {boolean} Whether the color palette is expanded (non-list, editable views) */
    get isExpanded() {
        return !this.props.canToggle && !this.props.readonly;
    }

    /** @param {number} colorIndex Color index to set on the record */
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
