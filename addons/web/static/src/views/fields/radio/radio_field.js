import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

let nextId = 0;
export class RadioField extends Component {
    static template = "web.RadioField";
    static props = {
        ...standardFieldProps,
        orientation: { type: String, optional: true },
        label: { type: String, optional: true },
        domain: { type: [Array, Function], optional: true },
    };
    static defaultProps = {
        orientation: "vertical",
    };

    setup() {
        this.id = `radio_field_${nextId++}`;
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData(async (orm, props) => {
                const { relation } = props.record.fields[props.name];
                const domain = getFieldDomain(props.record, props.name, props.domain);
                const kwargs = {
                    specification: { display_name: 1 },
                    domain,
                };
                const { records } = await orm.call(relation, "web_search_read", [], kwargs);
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
    displayName: _t("Radio"),
    supportedOptions: [
        {
            label: _t("Display horizontally"),
            name: "horizontal",
            type: "boolean",
        },
    ],
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ options, string }, dynamicInfo) => ({
        orientation: options.horizontal ? "horizontal" : "vertical",
        label: string,
        domain: dynamicInfo.domain,
    }),
};

registry.category("fields").add("radio", radioField);
