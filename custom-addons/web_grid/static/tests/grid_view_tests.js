/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    nextTick,
    patchDate,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerScroll,
} from "@web/../tests/helpers/utils";
import { toggleMenuItem, toggleSearchBarMenu } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { hoverGridCell } from "./helpers";

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
                        <filter string="Selection" name="groupby_selection" domain="[]" context="{'group_by': 'selection_field'}"/>
                    </search>
                `,
                "task,false,form": `<form><field name="display_name"/></form>`,
                "task,false,search": `<search/>`,
            },
        };
        setupViewRegistries();
        target = getFixture();
        patchDate(2017, 0, 30, 0, 0, 0);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("GridView");

    QUnit.test("basic empty grid view", async function (assert) {
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
        assert.containsOnce(target, ".o_grid_buttons:visible");
        assert.containsNone(target, ".o_grid_custom_buttons");
        assert.containsOnce(target, ".o_grid_navigation_buttons");
        assert.strictEqual(
            target.querySelector(".o_grid_navigation_buttons button:first-child").textContent,
            " Today ",
            "The first navigation button should be the Today one."
        );
        assert.containsOnce(
            target,
            ".o_grid_navigation_buttons button > span.oi-arrow-left",
            "The previous button should be there"
        );
        assert.containsOnce(
            target,
            ".o_grid_navigation_buttons button > span.oi-arrow-right",
            "The next button should be there"
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
            "Mon,\nJan\u00A030",
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

    QUnit.test("basic empty grid view using a specific range by default", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                        <range name="week" string="Week" span="week" step="day" default="1"/>
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
        assert.containsN(
            target,
            ".o_grid_column_title.o_grid_highlightable",
            7,
            "It should have 7 column representing the dates on a week."
        );
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_grid_column_title.o_grid_highlightable")
            ),
            [
                "Sun,\nJan\u00A029",
                "Mon,\nJan\u00A030",
                "Tue,\nJan\u00A031",
                "Wed,\nFeb\u00A01",
                "Thu,\nFeb\u00A02",
                "Fri,\nFeb\u00A03",
                "Sat,\nFeb\u00A04",
            ],
            "check the columns title is correctly formatted when the range is week"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_title.o_grid_row_total",
            1,
            "It should have 1 column for the total"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_title.o_grid_highlightable.fw-bolder",
            "The column title containing the current date should not be there."
        );
        assert.strictEqual(
            target.querySelector(".o_grid_column_title.o_grid_highlightable.fw-bolder")
                .textContent,
            "Mon,\nJan\u00A030",
            "The current date should be Monday on 30 January"
        );
    });

    QUnit.test("basic grid view", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                        <range name="week" string="Week" span="week" step="day" default="1"/>
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
        });

        assert.containsN(
            target,
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)",
            14,
            "The number of cells containing numeric value and whom is not a total cell should be 14 (2 rows and 7 cells to represent the week)"
        );
        assert.containsOnce(
            target,
            ".o_grid_row.o_grid_highlightable.text-danger:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)",
            "In those 14 cells, one has a value less than 0 and so the text should be red"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_grid_row.o_grid_highlightable.text-danger:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
            ).textContent,
            "-3.50",
            "The cell with text color in red should contain `-3.50`"
        );
        assert.containsOnce(
            target,
            ".o_grid_row.o_grid_highlightable.o_grid_column_total.text-danger",
            "The cell containing the column total and in that column a cell is negative to also get a total negative should have text color in red"
        );
        assert.strictEqual(
            target.querySelector(".o_grid_row.o_grid_highlightable.o_grid_column_total.text-danger")
                .textContent,
            "-3.50"
        );
        assert.containsOnce(target, ".o_grid_row.o_grid_highlightable.o_grid_row_total.bg-danger");
        assert.strictEqual(
            target.querySelector(".o_grid_row.o_grid_highlightable.o_grid_row_total.bg-danger")
                .textContent,
            "-3.50"
        );
        assert.containsN(
            target,
            ".o_grid_row.o_grid_highlightable > div.bg-info",
            3,
            "The cell in the column of the current should have `bg-info` class as the header"
        );
        assert.containsN(target, ".o_grid_row.o_grid_row_title.o_grid_highlightable", 2);
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_grid_row.o_grid_row_title.o_grid_highlightable")
            ),
            ["P1 | BS task", "Webocalypse Now | Another BS task"]
        );
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-right");
        assert.containsNone(
            target,
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)",
            "No cell should be found because no records is found next week"
        );
        assert.containsOnce(target, ".o_view_nocontent", "No content div should be displayed");
        assert.containsNone(
            target,
            "div.bg-info",
            "No column should be the current date since we move in the following week."
        );
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-right");
        assert.containsNone(target, "div.o_grid_row_title", "should not have any cell");
    });

    QUnit.test("basic grouped grid view", async function (assert) {
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_grid_section.o_grid_section_title",
            1,
            "A section should be displayed (for the project P1)"
        );
        assert.strictEqual(
            target.querySelector(".o_grid_section.o_grid_section_title").textContent,
            "P1",
            "The title of the section should be the project name"
        );
        assert.containsN(
            target,
            ".o_grid_section:not(.o_grid_section_title,.o_grid_row_total)",
            7,
            "7 cells for the section should be displayed to represent the total per day of the section"
        );
        assert.containsOnce(
            target,
            ".o_grid_section.o_grid_row_total",
            "One cell should be displayed to display the total of the week for the whole section"
        );
        assert.strictEqual(
            target.querySelector(".o_grid_section.o_grid_row_total").textContent,
            "10:00",
            "The total of the section should be equal to 10 hours."
        );
        assert.containsN(
            target,
            ".o_grid_row.o_grid_row_title",
            2,
            "2 rows should be displayed below that section (one per task)"
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_grid_row.o_grid_row_title")),
            ["None", "BS task"]
        );
        assert.containsN(
            target,
            ".o_grid_row:not(.o_grid_row_title,.o_grid_row_total,.o_grid_column_total,.o_grid_add_line)",
            14,
            "7 cells per row should be displayed to get value per day in the current week"
        );
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(
                    ".o_grid_row:not(.o_grid_row_title,.o_grid_row_total,.o_grid_column_total,.o_grid_add_line)"
                )
            ),
            [
                // row 1
                "0:00",
                "0:00",
                "2:30",
                "0:00",
                "0:00",
                "0:00",
                "0:00",
                // row 2
                "0:00",
                "0:00",
                "0:00",
                "7:30",
                "0:00",
                "0:00",
                "0:00",
            ]
        );
        assert.containsN(
            target,
            ".o_grid_row.o_grid_row_total",
            2,
            "One cell per row should be displayed to display the total of the week"
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_grid_row.o_grid_row_total")),
            ["2:30", "7:30"]
        );
        assert.containsNone(
            target,
            ".o_grid_search_btn",
            "No search button should be displayed in the grid cells."
        );
        await hoverGridCell(target.querySelectorAll('.o_grid_section.o_grid_highlightable')[1]);
        await click(target, ".o_grid_cell button.o_grid_search_btn");

        // Click on next period to have no data
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-left");
        assert.containsNone(target, ".o_grid_section");
        assert.containsNone(
            target,
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)",
            "No cell should be found because no records is found next week"
        );
        assert.containsOnce(target, ".o_view_nocontent", "No content div should be displayed");
        assert.containsNone(
            target,
            "div.bg-info",
            "No column should be the current date since we move in the following week."
        );
    });

    QUnit.test("clicking on the info icon on a cell triggers a do_action for section rows", async function (assert) {
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });
        assert.containsNone(
            target,
            ".o_grid_search_btn",
            "No search button should be displayed in the grid cells."
        );
        await hoverGridCell(target.querySelectorAll('.o_grid_section.o_grid_highlightable')[1]);
        await click(target, ".o_grid_cell button.o_grid_search_btn");
    });

    QUnit.test("Add/remove groupbys in search view", async function (assert) {
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            searchViewArch: `
                    <search>
                        <filter string="Project" name="groupby_project" domain="[]" context="{'group_by': 'project_id'}"/>
                        <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                    </search>
                `,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await toggleSearchBarMenu(target);
        let groupBys = target.querySelectorAll("span.o_menu_item");
        let groupByProject, groupByTask;
        for (const gb of groupBys) {
            if (gb.textContent === "Task") {
                groupByTask = gb;
            } else {
                groupByProject = gb;
            }
        }
        await click(groupByTask, "");
        await click(groupByProject, "");
        assert.containsNone(target, ".o_grid_section");
        assert.containsN(target, ".o_grid_row_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "None | P1",
            "BS task | P1",
        ]);
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-right");
        assert.containsNone(target, ".o_grid_section");
        assert.containsN(target, ".o_grid_row_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "BS task | P1",
            "Another BS task | Webocalypse Now",
        ]);

        // Remove the group and check the default groupbys defined in the view are correctly used.
        await toggleSearchBarMenu(target);
        groupBys = target.querySelectorAll("span.o_menu_item");
        for (const gb of groupBys) {
            if (gb.textContent === "Task") {
                groupByTask = gb;
            } else {
                groupByProject = gb;
            }
        }
        await click(groupByTask, "");
        await click(groupByProject, "");
        assert.containsN(target, ".o_grid_section_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_section_title")), [
            "P1",
            "Webocalypse Now",
        ]);
        assert.containsN(target, ".o_grid_row_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "BS task",
            "Another BS task",
        ]);
    });

    QUnit.test("groupBy with a field", async function (assert) {
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            searchViewArch: `
                    <search>
                        <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                    </search>
                `,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await toggleSearchBarMenu(target);
        await click(target, "span.o_menu_item:not(.o_add_custom_filter)");
        assert.containsNone(target, ".o_grid_section");
        assert.containsN(target, ".o_grid_row_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "None",
            "BS task",
        ]);
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-right");
        assert.containsNone(target, ".o_grid_section");
        assert.containsN(target, ".o_grid_row_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "BS task",
            "Another BS task",
        ]);
    });

    QUnit.test("groupBy doesn't change the scale", async function (assert) {
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            searchViewArch: `
                    <search>
                        <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                    </search>
                `,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await click(target, ".scale_button_selection");
        await click(target, ".o_view_scale_selector .o_scale_button_month");
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector button.scale_button_selection")
                .textContent,
            "Month",
            "The active range should be Month"
        );
        await toggleSearchBarMenu(target)
        await click(target, "div.o_group_by_menu > span.o_menu_item");
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector button.scale_button_selection")
                .textContent,
            "Month",
            "The active range should still be Month"
        );
    });

    QUnit.test("groupBy with column field should not be supported", async function (assert) {
        patchDate(2017, 0, 25, 0, 0, 0);
        const grid = await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            searchViewArch: `
                    <search>
                        <filter string="Date" name="date" domain="[]" context="{'group_by': 'date'}"/>
                    </search>
                `,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.groupby, ["date:day", "task_id", "project_id"]);
                }
            },
        });

        patchWithCleanup(grid.env.services.notification, {
            add: (message, options) => {
                assert.strictEqual(
                    message,
                    "Grouping by the field used in the column of the grid view is not possible."
                );
                assert.strictEqual(options.type, "warning");
            },
        });

        await toggleSearchBarMenu(target);
        const groupByDropdown = target.querySelector(
            ".o_menu_item:not(.o_add_custom_filter)"
        ).parentNode;
        await toggleMenuItem(target, "Date");
        const dateOptionNodes = groupByDropdown.querySelectorAll(".o_item_option");
        await click(dateOptionNodes[0], "");
        await click(dateOptionNodes[1], "");
    });

    QUnit.test("DOM keys are unique", async function (assert) {
        serverData.models["analytic.line"].records = [
            { id: 12, project_id: 142, date: "2017-01-17", unit_amount: 0 },
            { id: 4, project_id: 143, date: "2017-01-18", unit_amount: 0 },
            { id: 5, project_id: 142, date: "2017-01-18", unit_amount: 0 },
            { id: 10, project_id: 31, date: "2017-01-18", unit_amount: 0 },
            { id: 22, project_id: 33, date: "2017-01-19", unit_amount: 0 },
            { id: 21, project_id: 99, date: "2017-01-19", unit_amount: 0 },
            { id: 1, project_id: 31, date: "2017-01-24", unit_amount: 2.5 },
            { id: 3, project_id: 143, date: "2017-01-25", unit_amount: 5.5 },
            { id: 2, project_id: 33, date: "2017-01-25", unit_amount: 2 },
        ];
        serverData.models.project.records = [
            { id: 31, display_name: "Rem" },
            { id: 33, display_name: "Rer" },
            { id: 142, display_name: "Sas" },
            { id: 143, display_name: "Sassy" },
            { id: 99, display_name: "Sar" },
        ];
        patchDate(2017, 0, 25, 0, 0, 0);

        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
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
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "Rem",
            "Rer",
            "Sassy",
        ]);
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-left");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "Sas",
            "Rem",
            "Sassy",
            "Rer",
            "Sar",
        ]);
    });

    QUnit.test("Group By Selection field", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                <field name="selection_field" type="row"/>
                <field name="date" type="col">
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
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "DEF",
            "GHI",
        ]);
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-left");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "ABC",
            "DEF",
        ]);
    });

    QUnit.test("Create record with Add button in grid view", async function (assert) {
        patchDate(2017, 1, 25, 0, 0, 0);

        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid display_empty="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                    <range name="year" string="Year" span="year" step="month"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                } else if (args.method === "create") {
                    assert.strictEqual(
                        args.args[0][0].date,
                        "2017-02-25",
                        "default date should be the current day"
                    );
                }
            },
        });

        assert.containsNone(target, ".o_grid_row_title");
        assert.containsNone(target, ".modal");
        assert.containsNone(target, ".o_view_nocontent");
        await click(
            $(target).find(".o_control_panel_main_buttons > :visible").get(0),
            ".o_grid_button_add"
        );
        assert.containsOnce(target, ".modal");
        await selectDropdownItem(target, "project_id", "P1");
        await selectDropdownItem(target, "task_id", "BS task");

        // input unit_amount
        await editInput(target, ".modal .o_field_widget[name=unit_amount] input", "4");

        // save
        await click(target, ".modal .modal-footer button.o_form_button_save");

        assert.containsOnce(
            target,
            ".o_grid_row_title",
            "the record should be created and a row should be added"
        );
        assert.strictEqual(target.querySelector(".o_grid_row_title").textContent, "P1 | BS task");
    });

    QUnit.test("Create record with Add button in grid view grouped", async function (assert) {
        patchDate(2017, 1, 25, 0, 0, 0);

        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid display_empty="1">
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                    <range name="year" string="Year" span="year" step="month"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                } else if (args.method === "create") {
                    assert.strictEqual(
                        args.args[0][0].date,
                        "2017-02-25",
                        "default date should be the current day"
                    );
                }
            },
        });

        assert.containsNone(target, ".o_grid_row_title");
        assert.containsNone(target, ".modal");
        assert.containsNone(target, ".o_view_nocontent");
        await click(
            $(target).find(".o_control_panel_main_buttons > :visible").get(0),
            ".o_grid_button_add"
        );
        assert.containsOnce(target, ".modal");
        await selectDropdownItem(target, "project_id", "P1");
        await selectDropdownItem(target, "task_id", "BS task");

        // input unit_amount
        await editInput(target, ".modal .o_field_widget[name=unit_amount] input", "4");

        // save
        await click(target, ".modal .modal-footer button.o_form_button_save");

        assert.containsOnce(
            target,
            ".o_grid_section_title",
            "the record should be created and a row should be added"
        );
        assert.strictEqual(target.querySelector(".o_grid_section_title").textContent, "P1");
        assert.containsOnce(
            target,
            ".o_grid_row_title",
            "the record should be created and a row should be added"
        );
        assert.strictEqual(target.querySelector(".o_grid_row_title").textContent, "BS task");
    });

    QUnit.test("switching active range", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_view_scale_selector button.scale_button_selection")
                .textContent,
            "Week",
            "The default active range should be the first one define in the grid view"
        );
        assert.containsN(
            target,
            ".o_grid_column_title.o_grid_highlightable",
            7,
            "It should have 7 columns (one for each day)"
        );
        await click(target, ".scale_button_selection");
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
        await click(target, ".o_view_scale_selector .o_scale_button_month");
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector button.scale_button_selection")
                .textContent,
            "Month",
            "The active range should be Month"
        );
        assert.containsN(
            target,
            ".o_grid_column_title.o_grid_highlightable",
            31,
            "It should have 31 columns (one for each day)"
        );
    });

    QUnit.test("clicking on the info icon on a cell triggers a do_action", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid>
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                } else if (
                    args.method === "get_views" &&
                    args.kwargs.views.find((v) => v[1] === "list")
                ) {
                    const context = args.kwargs.context;
                    const expectedContext = {
                        default_project_id: 31,
                        default_task_id: 1,
                        default_date: "2017-01-30",
                    };
                    for (const [key, value] of Object.entries(expectedContext)) {
                        assert.strictEqual(context[key], value);
                    }
                }
            },
        });

        assert.containsNone(
            target,
            ".o_grid_search_btn",
            "No search button should be displayed in the grid cells."
        );
        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        const cell = cells[1];
        await hoverGridCell(cell);
        await click(target, ".o_grid_cell button.o_grid_search_btn");
    });

    QUnit.test("editing a value [REQUIRE FOCUS]", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                } else if (args.method === "grid_update_cell") {
                    assert.strictEqual(
                        args.model,
                        "analytic.line",
                        "The update cell should be called in the current model."
                    );
                    const [domain, fieldName, value] = args.args;
                    const domainExpected = Domain.and([
                        [
                            ["project_id", "=", 31],
                            ["task_id", "=", 1],
                        ],
                        [
                            ["date", ">=", "2017-01-29"],
                            ["date", "<", "2017-01-30"],
                        ],
                    ]).toList({});
                    assert.deepEqual(domain, domainExpected);
                    assert.strictEqual(
                        fieldName,
                        "unit_amount",
                        "The value updated should be the measure field"
                    );
                    assert.strictEqual(
                        value,
                        2,
                        "The value should be the one entered by the user, that is 2"
                    );
                }
            },
        });

        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        const cell = cells[0];
        const cellContainer = cell.closest(".o_grid_highlightable");
        const columnTotal = target.querySelector(
            `.o_grid_row.o_grid_column_total[data-grid-column="${cellContainer.dataset.gridColumn}"]`
        );
        const [columnTotalHours, columnTotalMinutes] = (
            (columnTotal.textContent?.length && columnTotal.textContent.split(":")) || [0, 0]
        ).map((value) => Number(value));
        const rowTotal = target.querySelector(
            `.o_grid_row_total[data-grid-row="${cellContainer.dataset.gridRow}"]`
        );
        const [rowTotalHours, rowTotalMinutes] = (
            (rowTotal.textContent?.length && rowTotal.textContent.split(":")) || [0, 0]
        ).map((value) => Number(value));
        assert.strictEqual(cell.textContent, "0:00");
        await hoverGridCell(cell);
        assert.containsOnce(
            target,
            ".o_grid_cell",
            "The GridCell component should be mounted on the grid cell hovered."
        );
        const gridCellComponentEl = target.querySelector(".o_grid_cell");
        const gridCell = cell.closest(".o_grid_row");
        assert.strictEqual(
            gridCellComponentEl.style["grid-row"],
            gridCell.style["grid-row"],
            "The GridCell component should be mounted in the same cell than the one hovered in the grid view."
        );
        assert.strictEqual(
            gridCellComponentEl.style["grid-column"],
            gridCell.style["grid-column"],
            "The GridCell component should be mounted in the same cell than the one hovered in the grid view."
        );
        assert.strictEqual(
            gridCellComponentEl.style["z-index"],
            "1",
            "The GridCell component should be mounted in the same cell than the one hovered in the grid view."
        );
        await click(target, ".o_grid_cell");
        await nextTick();
        assert.containsOnce(target, ".o_grid_cell input");
        await editInput(target, ".o_grid_cell input", "2");
        await nextTick();
        assert.strictEqual(cell.textContent, "2:00");
        assert.strictEqual(
            columnTotal.textContent,
            `${columnTotalHours + 2}:${String(columnTotalMinutes).padStart(2, "0")}`
        );
        assert.strictEqual(
            rowTotal.textContent,
            `${rowTotalHours + 2}:${String(rowTotalMinutes).padStart(2, "0")}`
        );
    });

    QUnit.test("hide row total", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid hide_line_total="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsN(target, ".o_grid_row_title", 2);
        assert.containsNone(target, ".o_grid_row_total", "No row total should be displayed");
        assert.containsN(target, ".o_grid_column_total", 7), "Columns total should be displayed";
    });

    QUnit.test("hide column total", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid hide_column_total="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsN(target, ".o_grid_row_title", 2);
        assert.containsN(target, ".o_grid_row_total", 3, "Rows total should be displayed");
        assert.containsNone(target, ".o_grid_column_total", " No column total should be displayed");
    });

    QUnit.test("display bar chart total", async function (assert) {
        serverData.models["analytic.line"].records.push({
            id: 8,
            project_id: 142,
            task_id: 54,
            date: "2017-01-25",
            unit_amount: 4,
        });
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid barchart_total="1" editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsN(target, ".o_grid_row_title", 3);
        assert.containsN(target, ".o_grid_row_total", 5, "Rows total should be displayed");
        assert.containsN(
            target,
            ".o_grid_column_total:not(.o_grid_bar_chart_container)",
            8,
            "8 cells should be visible to display the total per colunm"
        );
        assert.containsN(
            target,
            ".o_grid_bar_chart_container",
            7,
            "The bar chart total container should be displayed (one per column)"
        );
        assert.containsN(
            target,
            ".o_grid_bar_chart_total_pill",
            2,
            "2 bar charts totals should be displayed because the 5 others columns as a total equals to 0."
        );

        const barchartTotalNodes = target.querySelectorAll(".o_grid_bar_chart_total_pill");
        const expectedBarchartTotalHeightArray = ["", "", "", "", "", "", ""];
        for (let index = 0; index < barchartTotalNodes.length; index++) {
            assert.strictEqual(
                barchartTotalNodes[index].textContent,
                expectedBarchartTotalHeightArray[index]
            );
        }

        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        const cell = cells[0];
        assert.strictEqual(cell.textContent, "0:00");
        await hoverGridCell(cell);
        await click(target, ".o_grid_cell");
        await nextTick();
        assert.containsOnce(target, ".o_grid_cell input");
        await editInput(target, ".o_grid_cell input", "2");
        assert.containsN(
            target,
            ".o_grid_bar_chart_total_pill",
            3,
            "3 bar chart totals should be now displayed because a new column as a total greater than 0."
        );
    });

    QUnit.test("row and column are highlighted when hovering a cell", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid barchart_total="1" editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsNone(
            target,
            ".o_grid_row.o_grid_highlightable.bg-700",
            "No cell should be highlighted"
        );
        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        const cell = cells[0];
        await hoverGridCell(cell);
        assert.containsN(
            target,
            ".o_grid_row.o_grid_highlightable.o_grid_highlighted.o_grid_row_highlighted",
            8,
            "8 cells should be highlighted (the cells in the same rows (title row included))"
        );
        assert.containsOnce(
            target,
            ".o_grid_row_total.o_grid_highlighted.o_grid_row_highlighted",
            "The row total should also be highlighted"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_title.o_grid_highlighted",
            "The column title in the same column then the cell hovered should be highlighted"
        );
    });

    QUnit.test("grid_anchor stays when navigating", async function (assert) {
        // create an action manager to test the interactions with the search view
        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await doAction(webClient, {
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
            context: {
                search_default_project_id: 31,
                grid_anchor: "2017-01-31",
            },
        });

        // check first column header
        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_column_title")).includes(
                "Tue,\nJan\u00A031"
            ),
            "The 31st of January should be displayed in the grid view."
        );

        // move to previous week, and check first column header
        await click(target, ".oi-arrow-left");
        assert.notOk(
            getNodesTextContent(target.querySelectorAll(".o_grid_column_title")).includes(
                "Tue,\nJan\u00A031"
            ),
            "The 31st of January should no longer be displayed in the grid view"
        );
        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_column_title")).includes(
                "Tue,\nJan\u00A024"
            ),
            "The 24th of January should be displayed in the grid view."
        );

        // remove the filter in the searchview
        await click(target, ".o_facet_remove");
        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_column_title")).includes(
                "Tue,\nJan\u00A024"
            ),
            "The 24th of January should be always displayed in the grid view even if we remove a filter in the search view"
        );
    });

    QUnit.test(
        "dialog should not close when clicking the link to many2one field",
        async function (assert) {
            // create an action manager to test the interactions with the search view
            const webClient = await createWebClient({
                serverData,
                async mockRPC(route, args) {
                    if (args.method === "grid_unavailability") {
                        return {};
                    } else if (route === "/web/dataset/call_kw/task/get_formview_id") {
                        return false;
                    }
                },
            });

            await doAction(webClient, {
                res_model: "analytic.line",
                type: "ir.actions.act_window",
                views: [[false, "grid"]],
            });

            await click(
                $(target).find(".o_control_panel_main_buttons > :visible").get(0),
                ".o_grid_button_add"
            );
            await nextTick();
            assert.containsOnce(target, ".modal[role='dialog']");

            await selectDropdownItem(target, "task_id", "BS task");
            await click(target, '.modal .o_field_widget[name="task_id"] button.o_external_button');
            // Clicking somewhere on the form dialog should not close it
            assert.containsN(target, ".modal[role='dialog']", 2);
            await click(target.querySelector(".modal[role='dialog']"));
            assert.containsN(target, ".modal[role='dialog']", 2);
        }
    );

    QUnit.test("grid with two tasks with same name, and widget", async function (assert) {
        serverData.models.task.records = [
            { id: 1, display_name: "Awesome task", project_id: 31 },
            { id: 2, display_name: "Awesome task", project_id: 31 },
        ];
        serverData.models["analytic.line"].records = [
            { id: 1, task_id: 1, date: "2017-01-30", unit_amount: 2 },
            { id: 2, task_id: 2, date: "2017-01-31", unit_amount: 5.5 },
        ];
        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await doAction(webClient, {
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
            context: { search_default_groupby_task: 1 }, // to avoid creating a new grid view to remove project_id in rows
        });

        assert.containsN(target, ".o_grid_row_title", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_grid_row_title")), [
            "Awesome task",
            "Awesome task",
        ]);
    });

    QUnit.test("test grid cell formatting with float_time widget", async function (assert) {
        patchDate(2017, 0, 24, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            groupBy: ["task_id", "project_id"],
            arch: `<grid>
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
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

        assert.containsOnce(
            target,
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
            ).textContent,
            "2:30",
            "Check if the cell is correctly formatted as float time"
        );
        assert.containsOnce(
            target,
            ".o_grid_column_total:not(.o_grid_row_title,.o_grid_row_total,.o_grid_bar_chart_container)"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_grid_column_total:not(.o_grid_row_title,.o_grid_row_total,.o_grid_bar_chart_container) span"
            ).textContent,
            "2:30",
            "check format time is used"
        );
        assert.containsOnce(target, ".o_grid_row.o_grid_highlightable.o_grid_row_total");
        assert.strictEqual(
            target.querySelector(".o_grid_row.o_grid_highlightable.o_grid_row_total").textContent,
            "2:30",
            "check format time is used"
        );
    });

    QUnit.test(
        "The help content is not displayed instead of the grid with `display_empty` is true in the grid tag",
        async function (assert) {
            patchDate(2022, 0, 1, 0, 0, 0); // to be sure no data is found
            await makeView({
                type: "grid",
                resModel: "analytic.line",
                serverData,
                arch: `<grid display_empty="1">
                    <field name="project_id" type="row"/>
                    <field name="date" type="col">
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

            assert.containsNone(target, ".o_view_nocontent", "No content div should be displayed");
        }
    );

    QUnit.test("create_inline: test add a line in the grid view", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid create_inline="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsNone(
            target,
            ".o_grid_button_add:visible",
            "'Add a line' control panel button should not be visible"
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_grid_renderer .o_grid_add_line a")),
            ["Add a line "],
            "A button `Add a line` should be displayed in the grid view"
        );
        await click(target, ".o_grid_renderer .o_grid_add_line a");
        assert.containsOnce(target, ".modal");
        await click(target, ".modal .modal-footer button.o_form_button_cancel");
        await click(target, ".o_grid_navigation_buttons button span.oi-arrow-right");
        assert.containsNone(
            target,
            ".o_grid_add_line a",
            "No Add a line button should be displayed when no data is found"
        );
        assert.containsOnce(
            target,
            ".o_grid_button_add:visible",
            "'Add a line' control panel button should be visible"
        );
    });

    QUnit.test(
        "create_inline=true and display_empty=true: test add a line in the grid view",
        async function (assert) {
            await makeView({
                type: "grid",
                resModel: "analytic.line",
                serverData,
                arch: `<grid create_inline="1" display_empty="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
                async mockRPC(route, args) {
                    if (args.method === "grid_unavailability") {
                        return {};
                    }
                },
                domain: Domain.FALSE.toList({}),
            });
            assert.containsOnce(
                target,
                ".o_grid_add_line a",
                "The Add a line button should be displayed even if there is no data"
            );
            assert.containsNone(
                target,
                ".o_grid_button_add:visible",
                "The 'Add a line' button in the control panel should not be visible."
            );
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_grid_renderer .o_grid_add_line a")),
                ["Add a line "],
                "A button `Add a line` should be displayed in the grid view"
            );
            await click(target, ".o_grid_add_line a");
            assert.containsOnce(target, ".modal");
            await click(target, ".modal .modal-footer button.o_form_button_cancel");
            assert.containsOnce(
                target,
                ".o_grid_add_line a",
                "No Add a line button should be displayed when no data is found"
            );
            assert.containsNone(
                target,
                ".o_grid_button_add:visible",
                "'Add a line' control panel button should be visible"
            );
        }
    );

    QUnit.test("create/edit disabled for readonly grid view", async function (assert) {
        serverData.models["analytic.line"].fields.validated = {
            string: "Validation",
            type: "boolean",
            group_operator: "bool_or",
        };
        serverData.models["analytic.line"].records.push({
            id: 8,
            project_id: 142,
            task_id: 54,
            date: "2017-01-25",
            unit_amount: 4,
            validated: true,
        });
        patchDate(2017, 0, 25, 0, 0, 0);
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid editable="1">
                <field name="validated" type="readonly"/>
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="day" string="Day" span="day" step="day"/>
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });
        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        let cell = cells[0];
        await hoverGridCell(cell);
        assert.containsOnce(target, ".o_grid_cell .o_grid_search_btn");
        assert.containsNone(
            target,
            ".o_grid_cell.o_field_cursor_disabled",
            "The cell should not be in readonly"
        );
        await triggerEvent(target, ".o_grid_cell", "mouseout");
        cell = cells[1];
        await hoverGridCell(cell);
        assert.containsOnce(target, ".o_grid_cell .o_grid_search_btn");
        assert.containsOnce(
            target,
            ".o_grid_cell.o_field_cursor_disabled",
            "The cell should be in readonly since at least one timesheet is validated in that cell"
        );
        await click(target, "button.o_grid_search_btn");
    });

    QUnit.test(
        "display the empty grid without None line when there is no data",
        async function (assert) {
            await makeView({
                type: "grid",
                resModel: "analytic.line",
                serverData,
                arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
                async mockRPC(route, args) {
                    if (args.method === "grid_unavailability") {
                        return {};
                    }
                },
                domain: Domain.FALSE.toList({}),
            });

            assert.containsNone(
                target,
                ".o_grid_section_title",
                "No section should be displayed to display 'None'"
            );
            assert.containsNone(
                target,
                ".o_grid_row_title",
                "No row should be added to display 'None'"
            );
        }
    );

    QUnit.test('ensure the "None" is displayed in multi-level groupby', async function (assert) {
        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await doAction(webClient, {
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[1, "grid"]],
            context: {
                search_default_project_id: 31,
                search_default_groupby_task: 1,
                search_default_groupby_selection: 1,
                grid_anchor: "2017-01-24",
            },
        });

        assert.containsNone(
            target,
            ".o_grid_section",
            "No section should be displayed since the section field is not first in the groupby"
        );
        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_row_title")).includes(
                "None | ABC"
            ),
            "'None' should be displayed"
        );
    });

    QUnit.test('Group By selection field without passing selection field in data', async function (assert) {
        serverData.models["analytic.line"].records.push({
            id: 6,
            project_id: 142,
            task_id: 12,
            date: "2017-01-24",
            unit_amount: 7.0,
        });

        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        await doAction(webClient, {
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[1, "grid"]],
            context: {
                search_default_groupby_selection: 1,
                grid_anchor: "2017-01-24",
            },
        });

        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_row_title")).includes(
                "None"
            ),
            "'None' should be displayed."
        );
    });

    QUnit.test("stop edition when the user clicks outside", async function (assert) {
        const arch = serverData.views["analytic.line,false,grid"].replace(
            "<grid>",
            '<grid editable="1">'
        );
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
        const cell = cells[1];
        await hoverGridCell(cell);
        await click(target, ".o_grid_cell");
        await nextTick();

        assert.containsOnce(target, ".o_grid_cell input", "The cell should be in edit mode");

        await click(target, ".o_grid_view");
        assert.containsNone(
            target,
            ".o_grid_cell input",
            "The GridCell should no longer be visible and so no cell is in edit mode."
        );
    });

    QUnit.test(
        "display no content helper when no data and sample data is used (with display_empty='1')",
        async function (assert) {
            const arch = serverData.views["analytic.line,false,grid"].replace(
                "<grid>",
                `<grid create_inline="1"
                    form_view_id="%(timesheet_grid.my_timesheet_form_view)d"
                    editable="1"
                    display_empty="1"
                    sample="1"
                >`
            );

            await makeView({
                type: "grid",
                resModel: "analytic.line",
                serverData,
                arch,
                async mockRPC(route, args) {
                    if (args.method === "grid_unavailability") {
                        return {};
                    }
                },
                domain: Domain.FALSE.toList({}),
            });

            assert.containsOnce(
                target,
                ".o_view_sample_data",
                "The sample data should be displayed since no records is found."
            );
            assert.containsOnce(
                target,
                ".o_view_nocontent",
                "The action helper should also be displayed since the sample data is displayed even if display_empty='1'."
            );

            assert.containsOnce(
                target,
                ".o_grid_buttons .o_grid_button_add:visible",
                "The `Add a Line` button should be displayed when no content data is displayed to be able to create a record."
            );

            await click(target, ".o_grid_navigation_buttons span.oi-arrow-right");
            assert.containsNone(
                target,
                ".o_view_sample_data",
                "The sample data should no longer be displayed since display_empty is true in the grid view"
            );
            assert.containsNone(
                target,
                ".o_view_nocontent",
                "The no content helper should no longer be displayed since display_empty is true in the grid view."
            );
            assert.containsNone(
                target,
                ".o_grid_buttons .o_grid_button_add:visible",
                "The `Add a Line` button should no longer be displayed near the `Today` one since the no content helper is not displayed."
            );
            assert.containsOnce(
                target,
                ".o_grid_grid .o_grid_row.o_grid_add_line.position-md-sticky",
                "The `Add a Line` button should be displayed in the grid view since create_inline='1'"
            );
        }
    );

    QUnit.test("Only relevant grid rows are rendered with larger recordsets", async (assert) => {
        // Setup: generates 100 new tasks and related analytic lines distributed
        // in all available projects, deterministically based on their ID.
        const { fields: alFields, records: analyticLines } = serverData.models["analytic.line"];
        const { records: tasks } = serverData.models["task"];
        const { records: projects } = serverData.models["project"];
        const selectionValues = alFields.selection_field.selection;
        const today = luxon.DateTime.local().toFormat("yyyy-MM-dd");
        for (let id = 100; id < 200; id++) {
            const projectId = projects[id % projects.length].id;
            tasks.push({
                id,
                display_name: `BS task #${id}`,
                project_id: projectId,
            });
            analyticLines.push({
                id,
                project_id: projectId,
                task_id: id,
                selection_field: selectionValues[id % selectionValues.length][0],
                date: today,
                unit_amount: (id % 10) + 1, // 1 to 10
            });
        }

        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: /* xml */ `
                <grid>
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
            async mockRPC(_route, { method }) {
                if (method === "grid_unavailability") {
                    return {};
                }
            },
        });

        /**
         * Returns unique "data-grid-row" attributes to check for rows equality
         * @returns {string[]}
         */
        const getCurrentRows = () => [
            ...new Set([...grid.children].map((el) => el.dataset.gridRow)),
        ];

        const content = target.querySelector(".o_content");
        const grid = target.querySelector(".o_grid_grid");
        const firstRow = grid.querySelector(".o_grid_column_title");
        content.style = "height: 600px; overflow: scroll;";

        // This is to ensure that the virtual rows will not be impacted by
        // sub-pixel calculations.
        await triggerScroll(content, { top: 0 });

        const initialRows = getCurrentRows();
        let currentRows = initialRows;

        assert.strictEqual(content.scrollTop, 0, "content should be scrolled to the top");
        assert.strictEqual(content.offsetHeight, 600, "content should have its height fixed");
        // ! This next assertion is important: it ensures that the grid rows are
        // ! hard-coded so that the virtual hook can work with it. Adapt this test
        // ! accordingly should the row height change.
        assert.strictEqual(
            grid.clientHeight -
                firstRow.offsetHeight /* first row is "auto" so we don't count it */,
            (tasks.length - 1) /* ignore total row */ * 48 /* base grid row height */,
            "grid content should be the height of its row height times the amount of records"
        );
        assert.ok(currentRows.length < tasks.length, "not all rows should be displayed");

        // Scroll to the middle of the grid
        await triggerScroll(content, { top: content.scrollHeight / 2 });

        assert.notDeepEqual(currentRows, getCurrentRows(), "rows should be different");
        assert.ok(getCurrentRows().length < tasks.length, "not all rows should be displayed");
        currentRows = getCurrentRows();

        // Scroll to the end of the grid
        await triggerScroll(content, { top: content.scrollHeight });

        assert.notDeepEqual(currentRows, getCurrentRows(), "rows should be different");
        assert.ok(getCurrentRows().length < tasks.length, "not all rows should be displayed");

        // Scroll back to top
        await triggerScroll(content, { top: 0 });

        assert.deepEqual(getCurrentRows(), initialRows, "rows should be the same as initially");
    });

    QUnit.test("Edition navigate with tab/shift+tab and enter key", async (assert) => {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        function checkGridCellInRightPlace(expectedGridRow, expectedGridColumn) {
            const gridCell = target.querySelector(".o_grid_cell");
            assert.strictEqual(gridCell.dataset.gridRow, expectedGridRow);
            assert.strictEqual(gridCell.dataset.gridColumn, expectedGridColumn);
        }

        const firstCell = target.querySelector(".o_grid_row[data-row='1'][data-column='0']");
        assert.strictEqual(firstCell.dataset.gridRow, "2");
        assert.strictEqual(firstCell.dataset.gridColumn, "2");
        await hoverGridCell(firstCell, ".o_grid_cell_readonly");
        assert.containsOnce(
            target,
            ".o_grid_cell",
            "The GridCell component should be mounted on the grid cell hovered."
        );
        checkGridCellInRightPlace(firstCell.dataset.gridRow, firstCell.dataset.gridColumn);
        await click(target, ".o_grid_cell");
        await nextTick();

        // Go to the next cell
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "tab" });
        checkGridCellInRightPlace("2", "3");

        // Go to the previous cell
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("2", "2");

        // Go the cell below
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "enter" });
        checkGridCellInRightPlace("3", "2");

        // Go up since it is the cell in the row
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "enter" });
        checkGridCellInRightPlace("2", "3");

        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("2", "2");

        // Go to the last editable cell in the grid view since it is the first cell.
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("3", "8");

        // Go back to the first cell since it is the last cell in grid view.
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "tab" });
        checkGridCellInRightPlace("2", "2");

        // Go to the last editable cell in the grid view since it is the first cell.
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "shift+tab" });
        checkGridCellInRightPlace("3", "8");

        // Go back to the first cell since it is the last cell in grid view.
        await triggerEvent(target, ".o_grid_cell input", "keydown", { key: "enter" });
        checkGridCellInRightPlace("2", "2");
    });

    QUnit.test("Add custom buttons in grid view", async function (assert) {
        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `<grid editable="1">
                <button name="action_test" string="Test" />
                <button name="action_test_invisible" string="Test Invisible" invisible="not context.get('coucou', False)"/>
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });

        assert.containsN(
            target,
            "button[name='action_test']",
            2, // the second one is invisible for responsive.
            "The custom button should be visible",
        );
        assert.containsNone(target, "button[name='action_test_invisible']");
    });

    QUnit.test("date should be grouped by month in year range", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "grid",
            resModel: "analytic.line",
            serverData,
            arch: `
                <grid display_empty="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="year" string="Year" span="year" step="month"/>
                    </field>
                    <field name="unit_amount" type="measure"/>
                </grid>
            `,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                } else if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.groupby, ["date:month", "project_id", "task_id"]);
                }
            },
        });
    });

    QUnit.test(
        "display notification when the update of the grid cell cannot be done",
        async function (assert) {
            const grid = await makeView({
                type: "grid",
                resModel: "analytic.line",
                serverData,
                arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
                async mockRPC(route, args) {
                    if (args.method === "grid_unavailability") {
                        return {};
                    } else if (args.method === "grid_update_cell") {
                        assert.step("grid_update_cell");
                        return {
                            type: "ir.actions.client",
                            tag: "display_notification",
                            params: {
                                message: "test display a notification",
                                type: "danger",
                                sticky: false,
                            },
                        };
                    }
                },
            });
            patchWithCleanup(grid.env.services.action, {
                doAction: (data) => {
                    if (data.tag === "display_notification") {
                        assert.step(`notification_${data.params.type}`);
                    }
                },
            });

            const cells = target.querySelectorAll(".o_grid_row .o_grid_cell_readonly");
            const cell = cells[0];
            await hoverGridCell(cell);
            await click(target, ".o_grid_cell");
            await nextTick();
            assert.containsOnce(target, ".o_grid_cell input");
            await editInput(target, ".o_grid_cell input", "2");
            assert.verifySteps(["grid_update_cell", "notification_danger"]);
        }
    );

    QUnit.test(
        "grid: use the context in the action when a record will be created",
        async function (assert) {
            patchDate(2017, 1, 25, 0, 0, 0);

            await makeView({
                type: "grid",
                resModel: "analytic.line",
                serverData,
                arch: `<grid display_empty="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                        <range name="year" string="Year" span="year" step="month"/>
                    </field>
                    <field name="unit_amount" type="measure"/>
                </grid>`,
                async mockRPC(route, args) {
                    if (args.method === "grid_unavailability") {
                        return {};
                    } else if (args.method === "create") {
                        assert.strictEqual(
                            args.args[0][0].date,
                            "2017-02-25",
                            "default date should be the current day"
                        );
                    }
                },
                context: {
                    default_project_id: 31,
                },
            });
            assert.containsNone(target, ".o_grid_row_title");
            assert.containsNone(target, ".modal");
            assert.containsNone(target, ".o_view_nocontent");
            await click(
                $(target).find(".o_control_panel_main_buttons > :visible").get(0),
                ".o_grid_button_add"
            );
            assert.containsOnce(target, ".modal");
            assert.containsOnce(target, ".modal div[name=project_id]");
            assert.strictEqual(
                target.querySelector(".modal div[name=project_id] input").value,
                "P1"
            );
        }
    );

    QUnit.test("restore navigationInfo from previous state", async function (assert) {
        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });
        await doAction(webClient, {
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
        });
        await click(target, ".oi-arrow-left");
        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_column_title")).includes(
                "Tue,\nJan\u00A024"
            ),
            "The 24th of January should be displayed in the grid view"
        );
        await hoverGridCell((target.querySelectorAll(".o_grid_row .o_grid_cell_readonly"))[0]);
        await click(target, ".o_grid_cell button.o_grid_search_btn");
        await click(target.querySelector(".breadcrumb-item.o_back_button"));
        assert.ok(
            getNodesTextContent(target.querySelectorAll(".o_grid_column_title")).includes(
                "Tue,\nJan\u00A024"
            ),
            "The 24th of January should still be displayed in the grid view"
        );
    });

    QUnit.test("export navigationInfo when col is not a range", async function (assert) {
        serverData.views["analytic.line,false,grid"] = `<grid>
            <field name="project_id" type="row"/>
            <field name="task_id" type="col"/>
            <field name="unit_amount" type="measure" widget="float_time"/>
        </grid>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
        });
        await hoverGridCell(target.querySelectorAll(".o_grid_row .o_grid_cell_readonly")[0]);
        await click(target, ".o_grid_cell button.o_grid_search_btn");
        assert.containsOnce(target, ".o_list_view");
    });
});
