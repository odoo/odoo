import { defineSaleTimesheetModels } from "./sale_timesheet_test_helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    editInput,
    insertText,
    openFormView,
    openListView,
    registerArchs,
    start,
    step,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSaleTimesheetModels();
registerArchs({
    "account.analytic.line,false,form": `<form>
            <field name="so_line" widget="so_line_field"/>
        </form>`,
    "account.analytic.line,false,list": `<list editable="bottom">
            <field name="so_line" widget="so_line_field"/>
        </list>`,
    "project.task,false,form": `<form>
            <field name="timesheet_ids">
                <list editable="bottom">
                    <field name="so_line" widget="so_line_field"/>
                    <field name="is_so_line_edited" column_invisible="True"/>
                </list>
            </field>
        </form>`,
});
beforeEach(async () => {
    const pyEnv = await startServer();
    const so_line = pyEnv["sale.order.line"].create({ name: "Sale Order Line 1" });
    pyEnv["sale.order.line"].create({ name: "Sale Order Line 2" });
    pyEnv["account.analytic.line"].create({
        so_line: so_line,
    });
});

test("Check whether so_line_field widget works as intended in form view", async () => {
    const target = getFixture();
    await start();
    onRpc("account.analytic.line", "web_save", (args) => {
        expect(args.args[1].is_so_line_edited).toBe(true);
        step("web_save");
    });
    await openFormView("account.analytic.line");
    await editInput(target, ".o_field_widget[name=so_line] input", "Sale Order Line 2");
    await contains(".ui-autocomplete");
    await click(target.querySelector(".ui-menu-item"));
    await click(".o_form_button_save");
    await assertSteps(["web_save"]);
});

test("Check whether so_line_field widget works as intended in list view", async () => {
    const target = getFixture();
    await start();
    onRpc("account.analytic.line", "web_save", (args) => {
        expect(args.args[1].is_so_line_edited).toBe(true);
        step("web_save");
    });
    await openListView("account.analytic.line");
    await click(".o_data_cell");
    await insertText(".o_field_widget[name=so_line] input", "Sale Order Line 2", { replace: true });
    await contains(".ui-autocomplete");
    await click(target.querySelector(".ui-menu-item"));
    await click(target.querySelector(".o_searchview_input"));
    await assertSteps(["web_save"]);
});

test("Check whether so_line_field widget works as intended in sub-tree view of timesheets linked to a task", async () => {
    const target = getFixture();
    await start();
    onRpc("project.task", "web_save", (args) => {
        expect(args.args[1].timesheet_ids[0][2].is_so_line_edited).toBe(true);
        step("web_save");
    });
    await openFormView("project.task");
    await click(".o_field_x2many_list_row_add a");
    await insertText(".o_field_widget[name=so_line] input", "Sale Order Line 2", { replace: true });
    await contains(".ui-autocomplete");
    await click(target.querySelector(".ui-menu-item"));
    await click(".o_form_button_save");
    await assertSteps(["web_save"]);
});
