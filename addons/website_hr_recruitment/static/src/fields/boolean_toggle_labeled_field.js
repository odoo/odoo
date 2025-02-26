import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class BooleanToggleFieldLabeled extends BooleanToggleField {
    static template = "website_hr_recruitment.BooleanToggleFieldLabeled";
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
    ],
<<<<<<< master
||||||| 2108ad3f7c851eeceb84d7459485a18e1574fa64
    extractProps({ options }, dynamicInfo) {
        return {
            autosave: "autosave" in options ? Boolean(options.autosave) : true,
            readonly: dynamicInfo.readonly,
            true_label: options.true_label,
            false_label: options.false_label,
        };
    },
=======
    extractProps({ options }, dynamicInfo) {
        return {
            autosave: "autosave" in options ? Boolean(options.autosave) : true,
            readonly: dynamicInfo.readonly,
            true_label: _t(options.true_label),
            false_label: _t(options.false_label),
        };
    },
>>>>>>> 57873c5f09338f7b4e7a6193a1f13903e07a88e8
};

registry.category("fields").add("boolean_toggle_labeled", booleanToggleFieldLabeled);
