/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class BadgeSelectionField extends Component {
    get string() {
        switch (this.props.type) {
            case "many2one":
                return this.props.value ? this.props.value[1] : "";
            case "selection":
                return this.props.value !== false
                    ? this.props.options.find((o) => o[0] === this.props.value)[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.value;
        return this.props.type === "many2one" && rawValue ? rawValue[0] : rawValue;
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {Event} ev
     */
    onChange(value) {
        switch (this.props.type) {
            case "many2one":
                if (value === false) {
                    this.props.update(false);
                } else {
                    this.props.update(this.props.options.find((option) => option[0] === value));
                }
                break;
            case "selection":
                this.props.update(value);
                break;
        }
    }
}

BadgeSelectionField.template = "web.BadgeSelectionField";
BadgeSelectionField.props = {
    ...standardFieldProps,
    horizontal: { type: Boolean, optional: true },
    options: Object,
    placeholder: { type: String, optional: true },
};
BadgeSelectionField.extractProps = (fieldName, record, attrs) => {
    const getOptions = () => {
        switch (record.fields[fieldName].type) {
            case "many2one":
                return record.preloadedData[fieldName];
            case "selection":
                return record.fields[fieldName].selection;
            default:
                return [];
        }
    };
    return {
        horizontal: Boolean(attrs.options.horizontal),
        options: getOptions(),
    };
};
BadgeSelectionField.displayName = _lt("Selection");
BadgeSelectionField.supportedTypes = ["many2one", "selection"];
BadgeSelectionField.isEmpty = (record, fieldName) => record.data[fieldName] === false;

registry.category("fields").add("selection_badge", BadgeSelectionField);

export function preloadSelection(orm, record, fieldName) {
    const field = record.fields[fieldName];
    if (field.type !== "many2one") {
        return Promise.resolve();
    }

    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);

    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("selection_badge", preloadSelection);
