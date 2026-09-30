import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RemainingDaysField } from "@web/views/fields/remaining_days/remaining_days_field";

export class MrpRemainingDaysUnformattedField extends RemainingDaysField {
    static template = "mrp.MrpRemainingDaysUnformattedField"
}

export const mrpRemainingDaysUnformattedField = {
    component: MrpRemainingDaysUnformattedField,
    displayName: _t("Remaining Days"),
    supportedTypes: ["date", "datetime"],
};

registry.category("fields").add("mrp_remaining_days_unformatted", mrpRemainingDaysUnformattedField);
