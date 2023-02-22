/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class SelectionField extends Component {
    static template = "web.SelectionField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

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
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                return this.props.record.data[this.props.name]
                    ? this.props.record.data[this.props.name][1]
                    : "";
            case "selection":
                return this.props.record.data[this.props.name] !== false
                    ? this.options.find((o) => o[0] === this.props.record.data[this.props.name])[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return this.props.record.fields[this.props.name].type === "many2one" && rawValue
            ? rawValue[0]
            : rawValue;
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
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                if (value === false) {
                    this.props.record.update({ [this.props.name]: false });
                } else {
                    this.props.record.update({
                        [this.props.name]: this.options.find((option) => option[0] === value),
                    });
                }
                break;
            case "selection":
                this.props.record.update({ [this.props.name]: value });
                break;
        }
    }
}

export const selectionField = {
    component: SelectionField,
    displayName: _lt("Selection"),
    supportedTypes: ["many2one", "selection"],
    legacySpecialData: "_fetchSpecialRelation",
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("selection", selectionField);

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
