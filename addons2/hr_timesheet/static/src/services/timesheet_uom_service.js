/** @odoo-module */

import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { formatFloatTime, formatFloatFactor } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";

export const timesheetUOMService = {
    dependencies: ["company"],
    start(env, { company }) {
        const service = {
            get timesheetUOMId() {
                return company.currentCompany.timesheet_uom_id;
            },
            get timesheetWidget() {
                let timesheet_widget = "float_factor";
                if (session.uom_ids && this.timesheetUOMId in session.uom_ids) {
                    timesheet_widget = session.uom_ids[this.timesheetUOMId].timesheet_widget;
                }
                return timesheet_widget;
            },
            getTimesheetComponent(widgetName = this.timesheetWidget) {
                return registry.category("fields").get(widgetName, { component: FloatFactorField })
                    .component;
            },
            getTimesheetComponentProps(props) {
                const factorDependantComponents = ["float_toggle", "float_factor"];
                return factorDependantComponents.includes(this.timesheetWidget)
                    ? this._getFactorCompanyDependentProps(props)
                    : props;
            },
            _getFactorCompanyDependentProps(props) {
                const factor = company.currentCompany.timesheet_uom_factor || props.factor;
                return { ...props, factor };
            },
            get formatter() {
                if (this.timesheetWidget === "float_time") {
                    return formatFloatTime;
                }
                const factor = company.currentCompany.timesheet_uom_factor || 1;
                if (this.timesheetWidget === "float_toggle") {
                    return (value, options = {}) => formatFloat(value * factor, options);
                }
                return (value, options = {}) =>
                    formatFloatFactor(value, Object.assign({ factor }, options));
            },
        };
        if (!registry.category("formatters").contains("timesheet_uom")) {
            registry.category("formatters").add("timesheet_uom", service.formatter);
        }
        if (!registry.category("formatters").contains("timesheet_uom_no_toggle")) {
            registry.category("formatters").add("timesheet_uom_no_toggle", service.formatter);
        }
        return service;
    },
};

registry.category("services").add("timesheet_uom", timesheetUOMService);
