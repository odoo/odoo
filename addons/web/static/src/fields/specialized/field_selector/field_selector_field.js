// @ts-check

/** @module @web/fields/specialized/field_selector/field_selector_field - Model field path selector field for Char columns */

import { Component } from "@odoo/owl";
import { ModelFieldSelector } from "@web/components/model_field_selector/model_field_selector";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { formatChar } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class FieldSelectorField extends Component {
    static template = "web.FieldSelectorField";
    static components = { ModelFieldSelector };
    static props = {
        ...standardFieldProps,
        resModel: { type: String, optional: true },
        onlySearchable: { type: Boolean, optional: true },
        allowProperties: { type: Boolean, optional: true },
        followRelations: { type: Boolean, optional: true },
    };

    filter(fieldDef) {
        if (fieldDef.type === "separator") {
            // Don't show properties separator
            return false;
        }
        if (!this.props.allowProperties && fieldDef.type === "properties") {
            return false;
        }
        return !this.props.onlySearchable || fieldDef.searchable;
    }

    async update(value) {
        await this.props.record.update({ [this.props.name]: value });
    }

    //---- Getters ----
    get formattedValue() {
        return formatChar(this.props.record.data[this.props.name]);
    }

    get resModel() {
        return (
            this.props.record.data[this.props.resModel] || this.props.record.resModel
        );
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
        {
            label: _t("Only searchable"),
            name: "only_searchable",
            type: "string",
        },
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            allowProperties: options.allow_properties ?? true,
            followRelations: options.follow_relations ?? true,
            onlySearchable: exprToBoolean(options.only_searchable),
            resModel: options.model,
        };
    },
};

registry.category("fields").add("field_selector", fieldSelectorField);
