/** @odoo-module */

import { FloatToggleField } from '@web/views/fields/float_toggle/float_toggle_field';
import { TimesheetUOMMultiCompanyMixin } from '../../mixins/timesheet_uom_multi_company_mixin';

export class TimesheetFloatToggleField extends TimesheetUOMMultiCompanyMixin(FloatToggleField) {
    get factor() {
        return this.currentCompanyTimesheetUOMFactor || super.factor;
    }
}
