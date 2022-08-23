/** @odoo-module */

import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";
import { TimesheetUOMMultiCompanyMixin } from "../../mixins/timesheet_uom_multi_company_mixin";

export class TimesheetFloatFactorField extends TimesheetUOMMultiCompanyMixin(FloatFactorField) {
    get factor() {
        return this.currentCompanyTimesheetUOMFactor || super.factor;
    }
}
