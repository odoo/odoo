/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";
import { FloatToggleField } from "@web/views/fields/float_toggle/float_toggle_field";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class FloatTimeHourField extends FloatTimeField {
    get formattedValue() {
        const unitAmount = super.formattedValue;
        const [hours, minutes] = unitAmount.split(':').map(Number);
        let durationDisplay = `${hours}h`;
        if (minutes > 0) {
            durationDisplay += ` ${minutes}m`;
        }
        return durationDisplay;
    }
}

export class TimesheetUOM extends Component {
    static props = {
        ...standardFieldProps,
    };

    static template = "hr_timesheet.TimesheetUOM";

    static components = { FloatFactorField, FloatToggleField, FloatTimeField };

    setup() {
        this.timesheetUOMService = useService("timesheet_uom");
    }

    get timesheetComponent() {
        if (this.env.config.viewType === "kanban") {
            return FloatTimeHourField;
        }
        return this.timesheetUOMService.getTimesheetComponent();
    }

    get timesheetComponentProps() {
        return this.timesheetUOMService.getTimesheetComponentProps(this.props);
    }
}

export const timesheetUOM = {
    component: TimesheetUOM,
};

registry.category("fields").add("timesheet_uom", timesheetUOM);
