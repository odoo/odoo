import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RelativeDateField } from "@web/views/fields/relative_date/relative_date_field";

export class MrpRelativeDateUnformattedField extends RelativeDateField {
    static template = "mrp.MrpRelativeDateUnformattedField"
}

export const mrpRelativeDateUnformattedField = {
    component: MrpRelativeDateUnformattedField,
    displayName: _t("Remaining Days"),
    supportedTypes: ["date", "datetime"],
};

registry.category("fields").add("mrp_relative_date_unformatted", mrpRelativeDateUnformattedField);
