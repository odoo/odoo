/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class RadioField extends Component {
    static template = "web.RadioField";
    static props = {
        ...standardFieldProps,
        orientation: { type: String, optional: true },
    };
    static defaultProps = {
        orientation: "vertical",
    };

    static nextId = 0;

    static getItems(fieldName, record) {
        switch (record.fields[fieldName].type) {
            case "selection":
                return record.fields[fieldName].selection;
            case "many2one": {
                const value = record.preloadedData[fieldName] || [];
                return value.map((item) => [item.id, item.display_name]);
            }
            default:
                return [];
        }
    }

    setup() {
        this.id = `radio_field_${++RadioField.nextId}`;
    }

    get items() {
        return RadioField.getItems(this.props.name, this.props.record);
    }
    get string() {
        return this.props.record.activeFields[this.props.name].string;
    }
    get value() {
        switch (this.props.record.fields[this.props.name].type) {
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
        switch (this.props.record.fields[this.props.name].type) {
            case "selection":
                this.props.record.update({ [this.props.name]: value[0] });
                break;
            case "many2one":
                this.props.record.update({ [this.props.name]: value });
                break;
        }
    }
}

export const radioField = {
    component: RadioField,
    displayName: _lt("Radio"),
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ attrs }) => ({
        orientation: attrs.options.horizontal ? "horizontal" : "vertical",
    }),
    legacySpecialData: "_fetchSpecialMany2ones",
};

registry.category("fields").add("radio", radioField);

export async function preloadRadio(orm, record, fieldName) {
    const field = record.fields[fieldName];
    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);
    const records = await orm.searchRead(field.relation, domain, ["id"]);
    return await orm.call(field.relation, "name_get", [records.map((record) => record.id)]);
}

registry.category("preloadedData").add("radio", {
    loadOnTypes: ["many2one"],
    preload: preloadRadio,
});
