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
        resModel: { type: String, optional: true },
        allowProperties: { type: Boolean, optional: true },
        followRelations: { type: Boolean, optional: true },
        required: { type: Boolean, optional: true },
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
        return this.props.record.data[this.props.resModel] || this.props.record.resModel;
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
            followRelations: this.props.followRelations,
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
            followRelations: options.follow_relations ?? true,
<<<<<<< d02db249d8a87b29a910ab5a9c4db1cd5dd8aa31
||||||| 50fbe09a4f45d9e3b29846ae0cca3b73b068ff18
            onlySearchable: exprToBoolean(options.only_searchable),
=======
            onlySearchable: exprToBoolean(options.only_searchable),
            required: dynamicInfo.required,
>>>>>>> 8bb9ad552ffc75388cac5b2d72a3841f1f5df2e2
            resModel: options.model,
        };
    },
};

registry.category("fields").add("field_selector", fieldSelectorField);
