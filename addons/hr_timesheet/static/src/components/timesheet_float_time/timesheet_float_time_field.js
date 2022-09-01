/** @odoo-module */

import { FloatTimeField } from '@web/views/fields/float_time/float_time_field';
import { TimesheetUOMMultiCompanyMixin } from '../../mixins/timesheet_uom_multi_company_mixin';

export class TimesheetFloatTimeField extends TimesheetUOMMultiCompanyMixin(FloatTimeField) {}
