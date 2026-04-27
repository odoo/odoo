/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RemainingDaysField } from "@web/views/fields/remaining_days/remaining_days_field";

export class AppraisalRemainingDays extends RemainingDaysField {
    static template = "hr_appraisal.RemainingDaysField";

    /** @override **/
    get diffDays() {
        const result = super.diffDays;
        const state = this.props.record.data.state;
        if (result != null && ['done', 'cancel'].includes(state)) {
            // force the date's color to be grey
            return 1;
        }
        return result;
    }

    /** @override **/
    get diffString() {
        return this.formattedValue;
    }
}

export const appraisalRemainingDays = {
    component: AppraisalRemainingDays,
    displayName: _t("Remaining Days"),
    supportedTypes: ["date", "datetime"],
};

registry.category("fields").add("appraisal_remaining_days", appraisalRemainingDays);
