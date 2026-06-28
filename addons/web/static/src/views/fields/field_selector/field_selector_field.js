import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";
import { formatChar } from "../formatters";

export class FieldSelectorField extends Component {
    static template = "web.FieldSelectorField";
    static components = { ModelFieldSelector };
    static props = {
        ...standardFieldProps,
        model: { type: String },
        allowProperties: { type: Boolean, optional: true },
        followRelation: { type: [Boolean, Function], optional: true },
    };

    filter(fieldDef) {
        if (fieldDef.type === "separator") {
            // Don't show properties separator
            return false;
        }
        if (!this.props.allowProperties && fieldDef.type === "properties") {
            return false;
        }
        return true;
    }

    async update(value) {
        await this.props.record.update({ [this.props.name]: value });
    }

    //---- Getters ----
    get formattedValue() {
        return formatChar(this.props.record.data[this.props.name]);
    }

    get resModel() {
        return this.props.record.data[this.props.model] || this.props.model;
    }

    get selectorProps() {
        return {
            allowEmpty: !this.props.required,
            path: this.props.record.data[this.props.name],
            resModel: this.resModel,
            readonly: this.props.readonly,
            update: this.update.bind(this),
            isDebugMode: !!this.env.debug,
            filter: this.filter.bind(this),
            followRelation: this.props.followRelation,
        };
    }
}

export const fieldSelectorField = {
    component: FieldSelectorField,
    displayName: _t("Field Selector"),
    supportedTypes: ["char"],
    supportedOptions: [
        {
            label: _t("Follow relations"),
            name: "follow_relations",
            type: "boolean",
            default: true,
        },
        {
            label: _t("Model"),
            name: "model",
            type: "string",
        },
    ],
    extractProps({ options }) {
        return {
            allowProperties: options.allow_properties ?? true,
            followRelation: options.follow_relations ?? true,
            model: options.model,
        };
    },
};

registry.category("fields").add("field_selector", fieldSelectorField);
