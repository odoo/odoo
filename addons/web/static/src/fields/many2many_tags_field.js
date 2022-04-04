/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

import { CheckBox } from "@web/core/checkbox/checkbox";
import { ColorList } from "@web/core/colorlist/colorlist";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";

const { Component, useState } = owl;

export class Many2ManyTagsField extends Component {
    setup() {
        this.state = useState({
            hiddenTagsColors: {},
        });
        this.orm = useService("orm");
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
    tagColor(tag) {
        return `o_tag_color_${this.isTagHidden(tag) ? 0 : tag.colorIndex}`;
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

    get sources() {
        return [this.tagsSource];
    }
    get tagsSource() {
        return {
            placeholder: this.env._t("Loading..."),
            options: this.loadTagsSource.bind(this),
        };
    }

    getDomain() {
        return this.props.domain.toList(this.props.context);
    }

    async loadTagsSource(request) {
        const records = await this.orm.call(this.props.relation, "name_search", [], {
            name: request,
            args: [], // todo
            operator: "ilike",
            // limit: this.props.searchLimit + 1,
            context: this.props.record.getFieldContext(this.props.name),
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        return options;
    }

    onChange({ inputValue }) {
        console.log("onChange", inputValue);
        // if (!inputValue.length) {
        //     this.props.update(false);
        // }
    }
    onInput({ inputValue }) {
        console.log("onInput", inputValue);
        // this.state.isFloating = !this.props.value || this.props.value[1] !== inputValue;
    }

    onSelect(option) {
        console.log("onSelect", option);
        console.log("value", this.props.value);
    }
}

Many2ManyTagsField.components = {
    CheckBox,
    ColorList,
    Dropdown,
    DropdownItem,
    AutoComplete,
};
Many2ManyTagsField.template = "web.Many2ManyTagsField";
Many2ManyTagsField.defaultProps = {
    canEditColor: true,
    update: () => {},
};
Many2ManyTagsField.props = {
    ...standardFieldProps,
    canEditColor: { type: Boolean, optional: true },
    colorField: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    update: { type: Function, optional: true },
    relation: { type: String },
    domain: { type: Domain },
    context: { type: Object },
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
        canEditColor: !attrs.options.no_edit_color,
        update: (colorIndex, tagRecord) => {
            tagRecord.update(colorField, colorIndex);
            tagRecord.save();
        },
        relation: record.activeFields[fieldName].relation,
        domain: record.getFieldDomain(fieldName),
        context: record.getFieldContext(fieldName),
    };
};

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
