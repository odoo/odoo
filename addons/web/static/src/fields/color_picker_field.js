/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { _lt } from "@web/core/l10n/translation";

import { ColorList } from "@web/core/colorlist/colorlist";

const { Component, useState, useExternalListener } = owl;

export class ColorPickerField extends Component {
    setup() {
        this.state = useState({ isExpanded: false });
        useExternalListener(window, "click", this.onOutsideClick);
    }

    onOutsideClick(ev) {
        if (this.el.contains(ev.target)) return;
        if (this.state.isExpanded) {
            this.toggle(false);
        }
    }

    toggle(focus = true) {
        if (!this.isReadonly) {
            this.state.isExpanded = !this.state.isExpanded;
        }
        if (focus) {
            this.el.focus();
        }
    }

    get isReadonly() {
        return this.props.record.activeFields[this.props.name].modifiers.readonly;
    }

    switchColor(colorIndex) {
        this.props.update(colorIndex);
        this.toggle();
    }

    get currentColor() {
        return ColorPickerField.RECORD_COLORS[this.state.currentColorIndex];
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
ColorPickerField.RECORD_COLORS = [
    _lt("No color"),
    _lt("Red"),
    _lt("Orange"),
    _lt("Yellow"),
    _lt("Light blue"),
    _lt("Dark purple"),
    _lt("Salmon pink"),
    _lt("Medium blue"),
    _lt("Dark blue"),
    _lt("Fushia"),
    _lt("Green"),
    _lt("Purple"),
];

registry.category("fields").add("color_picker", ColorPickerField);
