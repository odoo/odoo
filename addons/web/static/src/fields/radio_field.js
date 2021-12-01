/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class RadioField extends Component {
    setup() {
        this.id = `radio_field_${++RadioField.nextId}`;
    }

    get items() {
        switch (this.props.type) {
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            case "many2one":
                return this.props.record.preloadedData
                    ? this.props.record.preloadedData[this.props.name]
                    : [];
            default:
                return [];
        }
    }
    get value() {
        switch (this.props.type) {
            case "selection":
                return this.props.value;
            case "many2one":
                return Array.isArray(this.props.value) ? this.props.value[0] : this.props.value;
            default:
                return null;
        }
    }

    /**
     * @param {any} value
     */
    onChange(value) {
        switch (this.props.type) {
            case "selection":
                this.props.update(value[0]);
                break;
            case "many2one":
                this.props.update(value);
                break;
        }
    }
}

Object.assign(RadioField, {
    props: {
        ...standardFieldProps,
    },
    template: "web.RadioField",
    nextId: 0,
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("radio", RadioField);

export async function fetchRadioPreloadedData(datapoint, fieldName) {
    const field = datapoint.fields[fieldName];
    if (field.type !== "many2one") {
        return null;
    }

    const orm = datapoint.model.orm;
    const records = await orm.searchRead(field.relation, [], ["id"]);
    return await orm.call(field.relation, "name_get", [records.map((record) => record.id)]);
}

registry.category("preloadedData").add("radio", fetchRadioPreloadedData);
