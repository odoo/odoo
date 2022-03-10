/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { ColorList } from "@web/core/colorlist/colorlist";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useState } = owl;

export class Many2ManyTagsField extends Component {
    setup() {
        this.state = useState({
            hiddenTagsColors: {},
        });
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
    isTagHidden(tag) {
        return !!this.state.hiddenTagsColors[tag.id];
    }
    switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.value.records.find((record) => record.data.id === tag.id);
        this.props.update(colorIndex, tagRecord);
        delete this.state.hiddenTagsColors[tag.id];
    }
    onTagVisibilityChange(isHidden, tag) {
        console.log(`should set isHiddenInKanban for tag ${tag} to: ${isHidden}`);
        if (isHidden) {
            this.state.hiddenTagsColors[tag.id] = this.props.value.records.find(
                (record) => record.data.id === tag.id
            ).data[this.props.colorField];
        } else {
            delete this.state.hiddenTagsColors[tag.id];
        }
    }
}

Many2ManyTagsField.components = {
    CheckBox,
    ColorList,
    Dropdown,
    DropdownItem,
};
Many2ManyTagsField.template = "web.Many2ManyTagsField";
Many2ManyTagsField.defaultProps = {
    canQuickEdit: true,
    update: () => {},
};
Many2ManyTagsField.props = {
    ...standardFieldProps,
    canQuickEdit: { type: Boolean, optional: true },
    colorField: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    update: { type: Function, optional: true },
};
Many2ManyTagsField.RECORD_COLORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
Many2ManyTagsField.displayName = _lt("Tags");
Many2ManyTagsField.supportedTypes = ["many2many"];
Many2ManyTagsField.fieldsToFetch = {
    display_name: { name: "display_name", type: "char" },
};

Many2ManyTagsField.extractProps = (fieldName, record, attrs) => {
    const colorField = attrs.options.color_field;
    return {
        colorField: colorField,
        canQuickEdit: !attrs.options.no_edit_color,
        update: (colorIndex, tagRecord) => {
            tagRecord.update(colorField, colorIndex);
            tagRecord.save();
        },
    };
};

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
