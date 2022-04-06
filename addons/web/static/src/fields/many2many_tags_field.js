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
import { sprintf } from "@web/core/utils/strings";

const { Component, useState } = owl;

export class Many2ManyTagsField extends Component {
    setup() {
        this.state = useState({
            autocompleteValue: "",
        });
        this.orm = useService("orm");
    }
    get tags() {
        const colorField = this.props.colorField;
        return this.props.value.records.map((record) => ({
            id: record.id,
            name: record.data.display_name,
            colorIndex: record.data[colorField],
        }));
    }
    tagColorClass(tag) {
        return `o_tag_color_${tag.colorIndex}`;
    }
    switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.value.records.find((record) => record.id === tag.id);
        tagRecord.update(this.props.colorField, colorIndex);
    }
    onTagVisibilityChange(isHidden, tag) {
        const tagRecord = this.props.value.records.find((record) => record.id === tag.id);
        tagRecord.update(this.props.colorField, isHidden ? 0 : 1);
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
        return Domain.and([
            this.props.domain,
            Domain.not([["id", "in", this.props.value.currentIds]]),
        ]).toList(this.props.context);
    }

    async loadTagsSource(request) {
        const records = await this.orm.call(this.props.relation, "name_search", [], {
            name: request,
            operator: "ilike",
            args: this.getDomain(),
            // limit: this.props.searchLimit + 1,
            context: this.props.context,
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        if (
            this.props.canQuickCreate &&
            request.length &&
            !this.tagExist(
                request,
                options.map((o) => o.label)
            )
        ) {
            options.push({
                label: sprintf(this.env._t(`Create "%s"`), escape(request)),
                value: request,
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                // action: this.onCreate.bind(this),
                type: "create",
            });
        }

        if (!options.length && this.props.canQuickCreate) {
            options.push({
                label: this.env._t("Start typing..."),
                classList: "o_m2o_start_typing",
                unselectable: true,
            });
        }

        if (!options.length && !this.props.canQuickCreate) {
            options.push({
                label: this.env._t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    }

    tagExist(name, additionalTagNames) {
        return [
            ...this.props.value.records.map((r) => r.data.display_name),
            ...additionalTagNames,
        ].some((n) => n === name);
    }

    onInput({ inputValue }) {
        console.log(inputValue);
        this.state.autocompleteValue = inputValue;
    }

    onSelect(option) {
        this.state.autocompleteValue = "";
        if (option.type === "create") {
            this.props
                .addItem({
                    context: this.props.context,
                })
                .then((record) => record.update("display_name", option.value));
        } else {
            this.props.linkItem({ resId: option.value });
        }
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
    canQuickCreate: true,
    update: () => {},
};
Many2ManyTagsField.props = {
    ...standardFieldProps,
    canEditColor: { type: Boolean, optional: true },
    canQuickCreate: { type: Boolean, optional: true },
    colorField: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    update: { type: Function, optional: true },
    relation: { type: String },
    domain: { type: Domain },
    context: { type: Object },
    linkItem: { type: Function },
    addItem: { type: Function },
    record: { type: Object },
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
        canQuickCreate: !attrs.options.no_quick_create,
        linkItem: record.data[fieldName].add.bind(record.data[fieldName]),
        addItem: record.data[fieldName].addNew.bind(record.data[fieldName]),
        record: record,
    };
};

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
