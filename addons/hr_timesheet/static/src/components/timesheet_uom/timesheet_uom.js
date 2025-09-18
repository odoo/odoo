import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FloatFactorField } from "@web/fields/basic/float_factor/float_factor_field";
import { FloatToggleField } from "@web/fields/basic/float_toggle/float_toggle_field";
import { FloatTimeField } from "@web/fields/basic/float_time/float_time_field";
import { standardFieldProps } from "@web/fields/standard_field_props";

import { Component } from "@odoo/owl";

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
