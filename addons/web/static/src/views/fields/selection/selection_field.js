/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class SelectionField extends Component {
    get options() {
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                return [...this.props.record.preloadedData[this.props.name]];
            case "selection":
                return this.props.record.fields[this.props.name].selection.filter(
                    (option) => option[0] !== false && option[1] !== ""
                );
            default:
                return [];
        }
    }
    get string() {
        switch (this.props.type) {
            case "many2one":
                return this.props.value ? this.props.value[1] : "";
            case "selection":
                return this.props.value !== false
                    ? this.options.find((o) => o[0] === this.props.value)[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.value;
        return this.props.type === "many2one" && rawValue ? rawValue[0] : rawValue;
    }
    get isRequired() {
        return this.props.record.isRequired(this.props.name);
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        const value = JSON.parse(ev.target.value);
        switch (this.props.type) {
            case "many2one":
                if (value === false) {
                    this.props.update(false);
                } else {
                    this.props.update(this.options.find((option) => option[0] === value));
                }
                break;
            case "selection":
                this.props.update(value);
                break;
        }
    }
}

SelectionField.template = "web.SelectionField";
SelectionField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};

SelectionField.displayName = _lt("Selection");
SelectionField.supportedTypes = ["many2one", "selection"];
SelectionField.legacySpecialData = "_fetchSpecialRelation";

SelectionField.isEmpty = (record, fieldName) => record.data[fieldName] === false;
SelectionField.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("selection", SelectionField);

export function preloadSelection(orm, record, fieldName) {
    const field = record.fields[fieldName];
    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("selection", {
    loadOnTypes: ["many2one"],
    preload: preloadSelection,
});
