/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class SelectionField extends Component {
    get options() {
        switch (this.props.type) {
            case "many2one":
                return this.props.record.specialData[this.props.name];
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            default:
                return [];
        }
    }
    get string() {
        switch (this.props.type) {
            case "many2one":
                return this.props.value ? this.props.value[1] : "";
            case "selection":
                return this.props.value ? Object.fromEntries(this.options)[this.props.value] : "";
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

Object.assign(SelectionField, {
    template: "web.SelectionField",
    props: {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    },
    isEmpty(record, fieldName) {
        return record.data[fieldName] === false;
    },
});

registry.category("fields").add("selection", SelectionField);

export function fetchSelectionSpecialData(datapoint, fieldName) {
    const field = datapoint.fields[fieldName];
    if (field.type !== "many2one") {
        return null;
    }

    const orm = datapoint.model.orm;
    const domain = [];
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("specialData").add("selection", fetchSelectionSpecialData);
