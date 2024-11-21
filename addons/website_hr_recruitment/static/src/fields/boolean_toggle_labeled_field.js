import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class BooleanToggleFieldLabeled extends BooleanToggleField {
    static template = "website_hr_recruitment.BooleanToggleFieldLabeled";
    static props = {
        ...BooleanToggleField.props,
        true_label: { type: String },
        false_label: { type: String },
    };
    setup() {
        super.setup(...arguments);
        useRecordObserver((record) => {
            this.state.label = record.data[this.props.name]
                ? this.props.true_label
                : this.props.false_label;
        });
    }
    async onChange(newValue) {
        super.onChange(...arguments);
        this.state.label = newValue ? this.props.true_label : this.props.false_label;
    }
}

export const booleanToggleFieldLabeled = {
    ...booleanToggleField,
    component: BooleanToggleFieldLabeled,
    displayName: _t("ToggleLabeled"),
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
        {
            label: _t("Label"),
            name: "true_label",
            type: "string",
            help: _t("A clickable label for the toggle. Contains text for the true state."),
        },
        {
            label: _t("Label"),
            name: "false_label",
            type: "string",
            help: _t("A clickable label for the toggle. Contains text for the false state."),
        },
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            autosave: "autosave" in options ? Boolean(options.autosave) : true,
            readonly: dynamicInfo.readonly,
            true_label: options.true_label,
            false_label: options.false_label,
        };
    },
};

registry.category("fields").add("boolean_toggle_labeled", booleanToggleFieldLabeled);
