import { beforeEach, expect, test } from "@odoo/hoot";
import { mountView, serverState } from "@web/../tests/web_test_helpers";

import { HRTimesheet, defineTimesheetModels, patchSession } from "./hr_timesheet_models";

HRTimesheet._views.form = `
    <form>
        <field name="project_id"/>
        <field name="task_id"/>
        <field name="unit_amount" widget="timesheet_uom_no_toggle"/>
    </form>
`;
defineTimesheetModels();

beforeEach(patchSession);

test("hr.timesheet (form): FloatTimeField is used when current company uom uses float_time widget", async () => {
    await mountView({
        type: "form",
        resModel: "account.analytic.line",
        resId: 1,
    });
    expect('div[name="unit_amount"] input').toHaveValue("01:00", {
        message: "unit_amount should be displayed as time",
    });
});

test("hr.timesheet (form): FloatTimeField is not dependent of timesheet_uom_factor of the current company when current company uom uses float_time widget", async () => {
    serverState.companies[0].timesheet_uom_factor = 2;
    await mountView({
        type: "form",
        resModel: "account.analytic.line",
        resId: 1,
    });
    expect('div[name="unit_amount"] input').toHaveValue("01:00", {
        message: "timesheet_uom_factor shouldn't be taken into account",
    });
});

test("hr.timesheet (form): FloatToggleField is not used when current company uom uses float_toggle widget, FloatFactorField is used instead", async () => {
    serverState.companies[0].timesheet_uom_id = 2;
    await mountView({
        type: "form",
        resModel: "account.analytic.line",
        resId: 1,
    });
    expect('div[name="unit_amount"] .o_field_float_toggle').not.toHaveCount(null, {
        message: "unit_amount shouldn't be displayed as float toggle",
    });
    expect('div[name="unit_amount"] input[inputmode="decimal"]').toBeVisible({
        message: "unit_amount should be displayed as float",
    });
    expect('div[name="unit_amount"] input').toHaveValue("1.00", {
        message: "unit_amount shouldn't be displayed as float and not as time",
    });
});

test("FloatFactorField is used when the current_company uom is not part of the session uom", async () => {
    serverState.companies[0].timesheet_uom_id = "dummy";
    await mountView({
        type: "form",
        resModel: "account.analytic.line",
        resId: 1,
    });
    expect('div[name="unit_amount"] input[inputmode="decimal"]').toBeVisible({
        message: "unit_amount should be displayed as float",
    });
    expect('div[name="unit_amount"] input').toHaveValue("1.00", {
        message: "unit_amount shouldn't be displayed as float and not as time",
    });
    expect('div[name="unit_amount"].o_field_float_toggle').not.toHaveCount(null, {
        message: "unit_amount shouldn't be displayed as float toggle",
    });
});

test("FloatFactorField is dependent of timesheet_uom_factor of the current company when current company uom uses float_toggle widget", async () => {
    serverState.companies[0].timesheet_uom_id = "dummy";
    serverState.companies[0].timesheet_uom_factor = 2;
    await mountView({
        type: "form",
        resModel: "account.analytic.line",
        resId: 1,
    });
    expect('div[name="unit_amount"] input').toHaveValue("2.00", {
        message: "timesheet_uom_factor should be taken into account",
    });
});
