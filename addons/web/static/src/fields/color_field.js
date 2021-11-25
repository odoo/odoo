/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";

import { ColorPickerDialog } from "@web/core/colorpicker/colorpicker_dialog";

const { Component } = owl;

export class ColorField extends Component {
    setup() {
        this.dialogService = useService("dialog");
    }

    onClick() {
        if (this.props.readonly) return;
        const self = this;
        this.dialogService.add(ColorPickerDialog, {
            onColorSelected(hex) {
                self.props.update(hex);
            },
            color: self.props.value || "#ffffff",
        });
    }
}
ColorField.template = "web.ColorField";

ColorField.props = {
    ...standardFieldProps,
};

registry.category("fields").add("color", ColorField);
