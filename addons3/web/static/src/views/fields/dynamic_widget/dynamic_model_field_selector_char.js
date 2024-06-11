/** @odoo-module */

import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";

import { DynamicModelFieldSelector } from "./dynamic_model_field_selector";
import { _t } from "@web/core/l10n/translation";

export class DynamicModelFieldSelectorChar extends CharField {
    static components = {
        ...CharField.components,
        DynamicModelFieldSelector,
    };

    static props = {
        ...CharField.props,
        resModel: { type: String, optional: true },
        onlySearchable: { type: Boolean, optional: true },
        followRelations: { type: Boolean, optional: true },
    };

    /**
     * Update record
     *
     * @param {string} value
     * @private
     */
    async _onRecordUpdate(value) {
        await this.props.record.update({ [this.props.name]: value });
    }

    //---- Getters ----
    get getSelectorProps() {
        return {
            path: this.props.record.data[this.props.name],
            resModel: this.getResModel(),
            readonly: this.props.readonly,
            record: this.props.record,
            recordProps: this.props,
            update: this._onRecordUpdate.bind(this),
            isDebugMode: !!this.env.debug,
            filter: this.filter.bind(this),
            followRelations: this.props.followRelations,
        };
    }

    filter(fieldDef) {
        return !this.props.onlySearchable || fieldDef.searchable;
    }

    getResModel(props = this.props) {
        const resModel = props.record.data[props.resModel];
        if (!resModel) {
            return props.record.resModel;
        }
        return resModel;
    }
}

DynamicModelFieldSelectorChar.template = "web.DynamicModelFieldSelectorChar";

export const dynamicModelFieldSelectorChar = {
    ...charField,
    component: DynamicModelFieldSelectorChar,
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
            followRelations: options.follow_relations ?? true,
            onlySearchable: archParseBoolean(options.only_searchable),
            resModel: options.model,
        };
    },
};

registry.category("fields").add("DynamicModelFieldSelectorChar", dynamicModelFieldSelectorChar);
