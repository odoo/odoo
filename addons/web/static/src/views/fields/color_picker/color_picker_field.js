import { ColorList } from "@web/core/colorlist/colorlist";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class ColorPickerField extends Component {
    static template = "web.ColorPickerField";
    static components = {
        ColorList,
        Dropdown,
    };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.dropdownState = useDropdownState();
    }

    get selectedColor() {
        return this.props.record.data[this.props.name] || 0;
    }

    get colors() {
        return ColorList.COLORS;
    }

    switchColor(colorIndex) {
        this.props.record.update({ [this.props.name]: colorIndex });
        this.dropdownState.close();
    }
}

export const colorPickerField = {
    component: ColorPickerField,
    supportedTypes: ["integer"],
    extractProps: ({}, dynamicInfo) => ({
        readonly: dynamicInfo.readonly,
    }),
};

registry.category("fields").add("color_picker", colorPickerField);
