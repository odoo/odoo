/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { booleanField, BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    static template = "web.BooleanToggleField";
    static props = {
        ...BooleanField.props,
        autosave: { type: Boolean, optional: true },
    };

    updateValue(value) {
        this.state.value = value;
        return this.props.record.update(
            { [this.props.name]: value },
            { save: this.props.autosave }
        );
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
                "If checked, the record will be saved immediately when the field is modified."
            ),
        },
    ],
    extractProps({ options }) {
        const props = booleanField.extractProps(...arguments);
        props.autosave = "autosave" in options ? Boolean(options.autosave) : true;
        return props;
    },
};

registry.category("fields").add("boolean_toggle", booleanToggleField);
