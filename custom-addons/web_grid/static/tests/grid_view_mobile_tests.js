/** @odoo-module */

/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { click, getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData, target;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                "analytic.line": {
                    fields: {
                        project_id: { string: "Project", type: "many2one", relation: "project" },
                        task_id: { string: "Task", type: "many2one", relation: "task" },
                        selection_field: {
                            string: "Selection Field",
                            type: "selection",
                            selection: [
                                ["abc", "ABC"],
                                ["def", "DEF"],
                                ["ghi", "GHI"],
                            ],
                        },
                        date: { string: "Date", type: "date" },
                        unit_amount: {
                            string: "Unit Amount",
                            type: "float",
                            group_operator: "sum",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            project_id: 31,
                            selection_field: "abc",
                            date: "2017-01-24",
                            unit_amount: 2.5,
                        },
                        {
                            id: 2,
                            project_id: 31,
                            task_id: 1,
                            selection_field: "def",
                            date: "2017-01-25",
                            unit_amount: 2,
                        },
                        {
                            id: 3,
                            project_id: 31,
                            task_id: 1,
                            selection_field: "def",
                            date: "2017-01-25",
                            unit_amount: 5.5,
                        },
                        {
                            id: 4,
                            project_id: 31,
                            task_id: 1,
                            selection_field: "def",
                            date: "2017-01-30",
                            unit_amount: 10,
                        },
                        {
                            id: 5,
                            project_id: 142,
                            task_id: 12,
                            selection_field: "ghi",
                            date: "2017-01-31",
                            unit_amount: -3.5,
                        },
                    ],
                },
                project: {
                    fields: {
                        name: { string: "Project Name", type: "char" },
                    },
                    records: [
                        { id: 31, display_name: "P1" },
                        { id: 142, display_name: "Webocalypse Now" },
                    ],
                },
                task: {
                    fields: {
                        name: { string: "Task Name", type: "char" },
                        project_id: { string: "Project", type: "many2one", relation: "project" },
                    },
                    records: [
                        { id: 1, display_name: "BS task", project_id: 31 },
                        { id: 12, display_name: "Another BS task", project_id: 142 },
                        { id: 54, display_name: "yet another task", project_id: 142 },
                    ],
                },
            },
            views: {
                "analytic.line,false,form": `
                    <form string="Add a line">
                        <group>
                            <group>
                                <field name="project_id"/>
                                <field name="task_id"/>
                                <field name="date"/>
                                <field name="unit_amount" string="Time spent"/>
                            </group>
                        </group>
                    </form>`,
                "analytic.line,false,list": `
                    <tree>
                        <field name="date" />
                        <field name="project_id" />
                        <field name="task_id" />
                        <field name="selection_field" />
                        <field name="unit_amount" />
                    </tree>`,
                "analytic.line,false,grid": `
                    <grid>
                        <field name="project_id" type="row"/>
                        <field name="task_id" type="row"/>
                        <field name="date" type="col">
                            <range name="week" string="Week" span="week" step="day"/>
                            <range name="month" string="Month" span="month" step="day"/>
                        </field>
                        <field name="unit_amount" type="measure" widget="float_time"/>
                    </grid>`,
                "analytic.line,1,grid": `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
                "analytic.line,false,search": `
                    <search>
                        <field name="project_id"/>
                        <filter string="Project" name="groupby_project" domain="[]" context="{'group_by': 'project_id'}"/>
                        <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                    </search>
                `,
                "task,false,form": `<form><field name="display_name"/></form>`,
                "task,false,search": `<search/>`,
            },
        };
        setupViewRegistries();
        target = getFixture();
        patchDate(2017, 0, 25, 0, 0, 0);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("GridView - Mobile");

    QUnit.test("basic empty grid view in mobile", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                        <range name="year" string="Year" span="year" step="month"/>
                    </field>
                    <field name="unit_amount" type="measure"/>
                </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
            domain: Domain.FALSE.toList({}),
        });

        assert.containsOnce(target, ".o_grid_view");
        assert.containsOnce(target, ".o_grid_renderer");
        assert.containsOnce(target, ".o_control_panel_main_buttons .d-xl-none .o_grid_buttons");
        assert.containsNone(target, ".o_grid_custom_buttons");
        assert.containsOnce(target, ".o_grid_navigation_buttons");
        assert.strictEqual(
            target.querySelector(".o_grid_navigation_buttons button:first-child").textContent,
            " Today ",
            "The first navigation button should be the Today one."
        );
        assert.containsOnce(
            target,
            ".o_grid_navigation_buttons > div > button > span.oi-arrow-left",
            "The previous button should be there"
        );
        assert.containsOnce(
            target,
            ".o_grid_navigation_buttons > div > button > span.oi-arrow-right",
            "The previous button should be there"
        );
        assert.containsOnce(target, ".o_view_scale_selector");
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector button.scale_button_selection")
                .textContent,
            "Day",
            "The default active range should be the first one define in the grid view"
        );
        await click(target, ".scale_button_selection");
        assert.containsOnce(
            target,
            ".o_view_scale_selector .o_scale_button_day",
            "The Day scale should be in the dropdown menu"
        );
        assert.containsOnce(
            target,
            ".o_view_scale_selector .o_scale_button_week",
            "The week scale should be in the dropdown menu"
        );
        assert.containsOnce(
            target,
            ".o_view_scale_selector .o_scale_button_month",
            "The month scale should be in the dropdown menu"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_title.o_grid_highlightable.fw-bolder",
            "The column title containing the date should be the current date"
        );
        assert.strictEqual(
            target.querySelector(".o_grid_column_title.o_grid_highlightable.fw-bolder")
                .textContent,
            "Wed,\nJan\u00A025",
            "The current date should be Monday on 30 January 2023"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_title.o_grid_highlightable",
            1,
            "It should have 1 column"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_title.o_grid_row_total",
            1,
            "It should have 1 column for the total"
        );
        assert.containsOnce(target, ".o_grid_column_title.o_grid_row_total");
        assert.strictEqual(
            target.querySelector(".o_grid_column_title.o_grid_row_total").textContent,
            serverData.models["analytic.line"].fields.unit_amount.string,
            "The column title of row totals should be the string of the measure field"
        );

        assert.containsNone(
            target,
            ".o_grid_add_line a",
            "No Add a line button should be displayed when create_inline is false (default behavior)"
        );
    });

    QUnit.test("grid view should open in day range for mobile", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid string="Timesheet">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsOnce(target, ".o_view_scale_selector");
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector button.scale_button_selection")
                .textContent,
            "Day",
            "The default active range should be the first one define in the grid view"
        );
    });
});
