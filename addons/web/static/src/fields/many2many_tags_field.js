/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

import { ColorPickerDialog } from "@web/core/colorpicker/colorpicker_dialog";

const { Component } = owl;

export class Many2ManyTagsField extends Component {
    setup() {
        this.dialogService = useService("dialog");
    }
    get tags() {
        const colorField = this.props.colorField;
        return this.props.value.records
            .filter((record) => !colorField || record.data[colorField])
            .map((record, i) => ({
                id: record.data.id,
                name: record.data.display_name,
                colorIndex: record.data[colorField] || i,
            }));
    }

    onClick() {
        if (this.isReadonly) return;
        const self = this;
        this.dialogService.add(ColorPickerDialog, {
            onColorSelected(hex) {
                self.props.update(hex);
            },
            color: self.props.colorField || "#ffffff",
        });
    }
}

Many2ManyTagsField.components = {
    ColorPickerDialog,
};
Many2ManyTagsField.template = "web.Many2ManyTagsField";
Many2ManyTagsField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    colorField: { type: String, optional: true },
};
Many2ManyTagsField.displayName = _lt("Tags");
Many2ManyTagsField.supportedTypes = ["many2many"];
Many2ManyTagsField.fieldsToFetch = {
    display_name: { name: "display_name", type: "char" },
};
Many2ManyTagsField.convertAttrsToProps = (attrs) => {
    return {
        colorField: attrs.options.color_field,
    };
};

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
