/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, editInput, getFixture } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

addModelNamesToFetch(["sale.order.line", "account.analytic.line"]);

let serverData;
let target;

QUnit.module("Sale Order Line Field Tests", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        const so_line = pyEnv["sale.order.line"].create([{ name: "Sale Order Line 1" }]);
        pyEnv["sale.order.line"].create([{ name: "Sale Order Line 2" }]);
        pyEnv["account.analytic.line"].create([
            {
                so_line: so_line,
            },
        ]);
        serverData = {
            views: {
                "account.analytic.line,false,form": `<form>
                        <field name="so_line" widget="so_line_field"/>
                    </form>`,
                "account.analytic.line,false,list": `<tree editable="bottom">
                        <field name="so_line" widget="so_line_field"/>
                    </tree>`,
                "project.task,false,form": `<form>
                    <field name="timesheet_ids">
                        <tree editable="bottom">
                            <field name="so_line" widget="so_line_field"/>
                            <field name="is_so_line_edited" column_invisible="True"/>
                        </tree>
                    </field>
                </form>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("Check whether so_line_field widget works as intended in form view", async function (assert) {
        assert.expect(4);
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].is_so_line_edited,
                        true,
                        "The SO line should be edited"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "account.analytic.line",
            views: [[false, "form"]],
        });
        await editInput(target, ".o_field_widget[name=so_line] input", "Sale Order Line 2");
        await contains(".ui-autocomplete");
        await click(target.querySelector(".ui-menu-item"));
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check whether so_line_field widget works as intended in list view", async function (assert) {
        assert.expect(4);
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].is_so_line_edited,
                        true,
                        "The SO line should be edited"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "account.analytic.line",
            views: [[false, "list"]],
        });
        await click(target.querySelectorAll(".o_data_cell")[0]);
        await editInput(target, ".o_field_widget[name=so_line] input", "Sale Order Line 2");
        await contains(".ui-autocomplete");
        await click(target.querySelector(".ui-menu-item"));
        await click(target);
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Check whether so_line_field widget works as intended in sub-tree view of timesheets linked to a task", async function (assert) {
        assert.expect(4);
        const { openView } = await start({
            serverData,
            async mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].timesheet_ids[0][2].is_so_line_edited,
                        true,
                        "The SO line should be edited"
                    );
                    assert.step("web_save");
                }
            },
        });
        await openView({
            res_model: "project.task",
            views: [[false, "form"]],
        });
        await click(target, ".o_field_x2many_list_row_add a");
        await editInput(target, ".o_field_widget[name=so_line] input", "Sale Order Line 2");
        await contains(".ui-autocomplete");
        await click(target.querySelector(".ui-menu-item"));
        await click(target, ".o_form_button_save");
        assert.verifySteps(["web_save"]);
    });
});
