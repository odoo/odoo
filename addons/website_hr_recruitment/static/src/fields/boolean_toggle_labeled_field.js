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
};

registry.category("fields").add("boolean_toggle_labeled", booleanToggleFieldLabeled);
