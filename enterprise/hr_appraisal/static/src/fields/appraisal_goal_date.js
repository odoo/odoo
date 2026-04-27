/** @odoo-module **/

import { DateTimeField, dateTimeField } from '@web/views/fields/datetime/datetime_field';
import { formatDate } from '@web/core/l10n/dates';
import { registry } from "@web/core/registry";

class AppraisalGoalDate extends DateTimeField {

    /**
     * @override
     * @returns { Date }
     */
    getFormattedValue() {
        const { data } = this.props.record;
        return formatDate(data.create_date);
    }
}

export const appraisalGoalDate = {
    ...dateTimeField,
    component: AppraisalGoalDate,
}

registry.category("fields").add('timeless_date',  appraisalGoalDate);
