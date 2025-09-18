// @ts-check

/** @module @web/fields/basic/boolean_toggle/boolean_toggle_field - Toggle switch field widget for Boolean columns */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BooleanField, booleanField } from "@web/fields/basic/boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    static template = "web.BooleanToggleField";
    static props = {
        ...BooleanField.props,
        autosave: { type: Boolean, optional: true },
    };

    /** @param {boolean} newValue @returns {Promise<void>} */
    async onChange(newValue) {
        this.state.value = newValue;
        const changes = { [this.props.name]: newValue };
        await this.props.record.update(changes, { save: this.props.autosave });
    }
}

export const booleanToggleField = {
    ...booleanField,
    component: BooleanToggleField,
    displayName: _t("Toggle"),
    supportedOptions: [
        {
            label: _t("Autosave"),
            name: "autosave",
            type: "boolean",
            default: true,
            help: _t(
                "If checked, the record will be saved immediately when the field is modified.",
            ),
        },
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            autosave: "autosave" in options ? Boolean(options.autosave) : true,
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("boolean_toggle", booleanToggleField);
