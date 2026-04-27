import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, click } from "@odoo/hoot-dom";
import { insertText } from "@web/../tests/utils";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { patchSession } from "@hr_timesheet/../tests/hr_timesheet_models";
import { defineTimesheetModels } from "./hr_timesheet_models";

defineTimesheetModels();
beforeEach(() => {
    patchSession();
});

describe.current.tags("desktop");

test("timesheet.grid (list)(timer): start & stop", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await advanceTime(100);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await advanceTime(100);
    expect(".btn_start_timer").toHaveCount(1);
});

test("timesheet.grid (list)(timer): start & stop, view is grouped", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        groupBy: ["project_id"],
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await advanceTime(100);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await advanceTime(100);
    expect(".btn_start_timer").toHaveCount(1);
});

test("timesheet.grid (list)(timer): start & stop, view is grouped multiple times", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        groupBy: ["project_id", "task_id", "name"],
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await advanceTime(100);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await advanceTime(100);
    expect(".btn_start_timer").toHaveCount(1);
});

test("timesheet.grid (list)(timer): start without a valid project", async () => {
    onRpc(({ method }) => {
        if (method === "action_start_new_timesheet_timer") {
            return false;
        }
    });
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await advanceTime(100);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await advanceTime(100);
    expect("div.o_notification_manager h5:contains(Invalid fields:)").toHaveCount(1, {
        message:
            "The default notification of 'required fields' of a Many2one relation should be raised.",
    });
});

test("timesheet.grid (list)(time): retain edited time after focus change", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `<list editable="bottom" js_class="timesheet_timer_list">
                <field name="name" />
                <field name="unit_amount" widget="timesheet_uom_timer" />
            </list>`,
    });
    const targetRow = ".o_data_row:nth-child(1)";
    await click(`${targetRow} .o_list_number`);
    await insertText(`${targetRow} .o_list_number input`, "45", { replace: true });
    await click(`${targetRow} .o_list_char`);
    await advanceTime(100);
    expect(`${targetRow} .o_list_number input`).toHaveValue("45:00");
});
