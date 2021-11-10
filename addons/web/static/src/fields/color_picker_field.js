/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { _lt } from "../core/l10n/translation";

const { Component } = owl;

export class ColorPickerField extends Component {}
ColorPickerField.template = "web.ColorPickerField";
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

ColorPickerField.props = {
    ...standardFieldProps,
};

registry.category("fields").add("color_picker", ColorPickerField);
