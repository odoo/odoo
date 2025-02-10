import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { booleanField, BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    static template = "web.BooleanToggleField";
    static props = {
        ...BooleanField.props,
        autosave: { type: Boolean, optional: true },
    };

    async onChange(newValue) {
        this.state.value = newValue;
        const changes = { [this.props.name]: newValue };
        await this.props.record.update(changes, { save: this.props.autosave });
    }

    get hasTooltip() {
        return this.tooltipHelp;
    }
    get tooltipHelp() {
        const field = this.props.record.fields[this.props.name];
        let help =  field.help || "";
        return help;
    }
    get tooltipInfo() {
        return JSON.stringify({
            field: {
                help: this.tooltipHelp,
            },
        });
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
    extractProps({ options }, dynamicInfo) {
        return {
            autosave: "autosave" in options ? Boolean(options.autosave) : true,
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("boolean_toggle", booleanToggleField);
