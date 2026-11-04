/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class AccrualLevelsX2ManyField extends X2ManyField {
    static template = "hr_holidays.AccrualLevelsX2ManyField";
}

export const accrualLevelsX2ManyField = {
    ...x2ManyField,
    component: AccrualLevelsX2ManyField,
};

registry.category("fields").add("accrual_levels_one2many", accrualLevelsX2ManyField);
