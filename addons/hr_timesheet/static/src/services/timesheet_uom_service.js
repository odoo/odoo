/** @odoo-module */

import { session } from "@web/session";
import { registry } from "@web/core/registry";

import { TimesheetFloatFactorField } from "../components/timesheet_float_factor/timesheet_float_factor_field";
import { TimesheetFloatTimeField } from "../components/timesheet_float_time/timesheet_float_time_field";
import { TimesheetFloatToggleField } from "../components/timesheet_float_toggle/timesheet_float_toggle";
import {FloatFactorField} from "@web/views/fields/float_factor/float_factor_field";

export const timesheetUomService = {
    dependencies: ["company"],
    start(env, { company }) {
        const timesheetUomWidget = { widget: "float_factor" };
        if (company.allowedCompanyIds.length) {
            const currentCompanyTimesheetUOMId = company.currentCompany.timesheet_uom_id || false;
            if (currentCompanyTimesheetUOMId) {
                timesheetUomWidget.widget = session.uom_ids[currentCompanyTimesheetUOMId].timesheet_widget;
            }
        }

        /**
         * Binding depending on Company Preference
         *
         * determine which widget will be the timesheet one.
         * Simply match the 'timesheet_uom' widget key with the correct
         * implementation (float_time, float_toggle, ...). The default
         * value will be 'float_factor'.
         **/
        const fieldRegistry = registry.category("fields");

        let TimesheetUoMField = null;

        if (timesheetUomWidget.widget === "float_toggle") {
            TimesheetUoMField = TimesheetFloatToggleField;
        } else if (timesheetUomWidget.widget === "float_time") {
            TimesheetUoMField = TimesheetFloatTimeField;
        } else {
            let fieldRegistryWidget = fieldRegistry.get(timesheetUomWidget.widget);
            if (fieldRegistryWidget === FloatFactorField) {
                fieldRegistryWidget = TimesheetFloatFactorField;
            }
            TimesheetUoMField = fieldRegistryWidget;
        }
        fieldRegistry.add("timesheet_uom", TimesheetUoMField);

        // widget timesheet_uom_no_toggle is the same as timesheet_uom but without toggle.
        // We can modify easly huge amount of days.
        let TimesheetUoMWithoutToggleField = TimesheetUoMField;
        if (timesheetUomWidget.widget === "float_toggle") {
            TimesheetUoMWithoutToggleField = TimesheetFloatFactorField;
        }
        fieldRegistry.add("timesheet_uom_no_toggle", TimesheetUoMWithoutToggleField);

        return timesheetUomWidget.widget;
    },
};

registry.category("services").add("timesheet_uom", timesheetUomService);
