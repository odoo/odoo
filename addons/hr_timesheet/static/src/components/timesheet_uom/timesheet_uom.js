import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { getTimesheetWidget } from "@hr_timesheet/utils/timesheet_uom";

import { Component, useProps } from "@odoo/owl";

export class TimesheetUOM extends Component {
    static template = "hr_timesheet.TimesheetUOM";

    // Make 'record' optional since this component can be called elsewhere and doesn't
    // use it.
    props = useProps({
        ...standardFieldProps,
        record: standardFieldProps.record.optional(),
    });

    get timesheetWidget() {
        return getTimesheetWidget();
    }

    /**
     * @param {string} fieldName
     */
    getTimesheetComponent(fieldName) {
        return registry.category("fields").get(fieldName, { component: FloatFactorField })
            .component;
    }

    get timesheetComponentProps() {
        const factorDependantComponents = ["float_toggle", "float_factor"];
        if (!factorDependantComponents.includes(this.timesheetWidget)) {
            return this.props;
        }
        const factor = user.activeCompany.timesheet_uom_factor || this.props.factor;
        return { ...this.props, factor, digits: [0, 2], trailingZeros: false };
    }
}

export const timesheetUOM = {
    component: TimesheetUOM,
};

registry.category("fields").add("timesheet_uom", timesheetUOM);
