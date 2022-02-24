/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { ColorList } from "@web/core/colorlist/colorlist";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class Many2ManyTagsField extends Component {
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
    switchColor(colorIndex, tag) {
        //Not sure about how to change and save a many2many field
        const record = this.props.value.records.filter((record) => record.data.id === tag.id)[0];
        record.update(this.props.colorField, colorIndex);
    }
}

Many2ManyTagsField.components = {
    CheckBox,
    ColorList,
    Dropdown,
    DropdownItem,
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
Many2ManyTagsField.RECORD_COLORS = [
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
Many2ManyTagsField.convertAttrsToProps = (attrs) => {
    return {
        colorField: attrs.options.color_field,
    };
};

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
