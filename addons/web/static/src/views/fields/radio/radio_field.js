/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

export class RadioField extends Component {
    static template = "web.RadioField";
    static props = {
        ...standardFieldProps,
        orientation: { type: String, optional: true },
        label: { type: String, optional: true },
        domain: { type: Array, optional: true },
    };
    static defaultProps = {
        orientation: "vertical",
    };

    static nextId = 0;

    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData(async (orm, props) => {
                const { relation } = props.record.fields[props.name];
                const kwargs = {
                    specification: { display_name: 1 },
                    domain: props.domain,
                };
                const { records } = await orm.call(relation, "unity_web_search_read", [], kwargs);
                return records.map((record) => [record.id, record.display_name]);
            });
        }
    }

    get items() {
        switch (this.type) {
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            case "many2one": {
                return this.specialData.data;
            }
            default:
                return [];
        }
    }
    get value() {
        switch (this.type) {
            case "selection":
                return this.props.record.data[this.props.name];
            case "many2one":
                return Array.isArray(this.props.record.data[this.props.name])
                    ? this.props.record.data[this.props.name][0]
                    : this.props.record.data[this.props.name];
            default:
                return null;
        }
    }

    /**
     * @param {any} value
     */
    onChange(value) {
        switch (this.type) {
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
    supportedOptions: [
        {
            label: _lt("Display horizontally"),
            name: "horizontal",
            type: "boolean",
        },
    ],
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ options, string }, dynamicInfo) => ({
        orientation: options.horizontal ? "horizontal" : "vertical",
        label: string,
        domain: dynamicInfo.domain(),
    }),
};

registry.category("fields").add("radio", radioField);
