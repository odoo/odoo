/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

export class BadgeSelectionField extends Component {
    static template = "web.BadgeSelectionField";
    static props = {
        ...standardFieldProps,
        domain: { type: Array, optional: true },
        size: { type: String, optional: true, validate: (s) => ["sm", "md", "lg"].includes(s), default: "md"},
    };

    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData((orm, props) => {
                const { relation } = props.record.fields[props.name];
                return orm.call(relation, "name_search", ["", props.domain]);
            });
        }
    }

    get options() {
        switch (this.type) {
            case "many2one":
                return this.specialData.data;
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            default:
                return [];
        }
    }

    get string() {
        switch (this.type) {
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
        return this.type === "many2one" && rawValue ? rawValue[0] : rawValue;
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {string | number | false} value
     */
    onChange(value) {
        switch (this.type) {
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

export const badgeSelectionField = {
    component: BadgeSelectionField,
    displayName: _t("Badges"),
    supportedTypes: ["many2one", "selection"],
    supportedOptions: [
        {
            label: "Size",
            name: "size",
            type: "selection",
            choices: [
                { label: "Small", value: "sm" },
                { label: "Medium", value: "md" },
                { label: "Large", value: "lg" },],
            default: "md",
        }
    ],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: (fieldInfo, dynamicInfo) => ({
        domain: dynamicInfo.domain(),
        size: fieldInfo.options.size,
    }),
};

registry.category("fields").add("selection_badge", badgeSelectionField);
