import { Plugin } from "@odoo/owl";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { formatFloatTime, formatFloatFactor } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";
import { user } from "@web/core/user";

/**
 * Returns the timesheet widget configured for the active company's UOM.
 * @returns {string}
 */
export function getTimesheetWidget() {
    const timesheetUOMId = user.activeCompany.timesheet_uom_id;
    if (session.uom_ids && timesheetUOMId in session.uom_ids) {
        return session.uom_ids[timesheetUOMId].timesheet_widget;
    }
    return "float_factor";
}

/**
 * Formats a timesheet value according to the active company's UOM settings.
 *
 * @param {number} value
 * @param {Object} [options]
 * @returns {string}
 */
export function formatTimesheetUOM(value, options = {}) {
    const timesheetWidget = getTimesheetWidget();
    if (timesheetWidget === "float_time") {
        return formatFloatTime(value, options);
    }
    const factor = user.activeCompany.timesheet_uom_factor || 1;
    if (timesheetWidget === "float_toggle") {
        return formatFloat(value * factor, options);
    }
    return formatFloatFactor(value, { factor, ...options });
}

registry
    .category("formatters")
    .add("timesheet_uom", formatTimesheetUOM)
    .add("timesheet_uom_no_toggle", formatTimesheetUOM);

export class TimesheetUOMPlugin extends Plugin {
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

    getTimesheetComponentProps(props) {
        const factorDependantComponents = ["float_toggle", "float_factor"];
        return factorDependantComponents.includes(this.timesheetWidget)
            ? this.#getFactorCompanyDependentProps(props)
            : props;
    }

    #getFactorCompanyDependentProps(props) {
        const factor = user.activeCompany.timesheet_uom_factor || props.factor;
        const digits = [0, 2];
        const trailingZeros = false;
        return { ...props, factor, digits, trailingZeros };
    }
}

services.add(TimesheetUOMPlugin);
