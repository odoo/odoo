import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    hover,
    press,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
    scroll,
} from "@odoo/hoot-dom";
import { animationFrame, mockDate, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    getService,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    selectFieldDropdownItem,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { WebClient } from "@web/webclient/webclient";

class Line extends models.Model {
    _name = "analytic.line";

    project_id = fields.Many2one({ string: "Project", relation: "project" });
    task_id = fields.Many2one({ string: "Task", relation: "task" });
    selection_field = fields.Selection({
        string: "Selection Field",
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });
    date = fields.Date();
    unit_amount = fields.Float({
        string: "Unit Amount",
        aggregator: "sum",
    });

    _records = [
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
    ];

    _views = {
        form: `
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
        list: `
            <list>
                <field name="date" />
                <field name="project_id" />
                <field name="task_id" />
                <field name="selection_field" />
                <field name="unit_amount" />
            </list>`,
        grid: `
            <grid>
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        "grid,1": `
            <grid>
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        search: `
            <search>
                <field name="project_id"/>
                <filter string="Project" name="groupby_project" domain="[]" context="{'group_by': 'project_id'}"/>
                <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                <filter string="Selection" name="groupby_selection" domain="[]" context="{'group_by': 'selection_field'}"/>
            </search>
        `,
    };
}

class Project extends models.Model {
    name = fields.Char();

    _records = [
        { id: 31, name: "P1" },
        { id: 142, name: "Webocalypse Now" },
    ];
}

class Task extends models.Model {
    name = fields.Char();
    project_id = fields.Many2one({ string: "Project", relation: "project" });

    _records = [
        { id: 1, name: "BS task", project_id: 31 },
        { id: 12, name: "Another BS task", project_id: 142 },
        { id: 54, name: "yet another task", project_id: 142 },
    ];

    _views = {
        form: `<form><field name="display_name"/></form>`,
    };
}

defineModels([Line, Project, Task]);

beforeEach(() => {
    mockDate("2017-01-30 00:00:00");
});

onRpc("grid_unavailability", () => ({}));
onRpc("has_group", () => true);

describe.tags("desktop");
describe("grid_view_desktop", () => {
    test("basic empty grid view", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
            domain: Domain.FALSE.toList({}),
        });

        expect(".o_grid_view").toHaveCount(1);
        expect(".o_grid_renderer").toHaveCount(1);
        expect(".o_grid_buttons:visible").toHaveCount(1);
        expect(".o_grid_custom_buttons").toHaveCount(0);
        expect(".o_grid_navigation_buttons").toHaveCount(1);
        expect(".o_grid_navigation_buttons button:eq(0)").toHaveText("Today", {
            message: "The first navigation button should be the Today one.",
        });
        expect(".o_grid_navigation_buttons button > span.oi-arrow-left").toHaveCount(1, {
            message: "The previous button should be there",
        });
        expect(".o_grid_navigation_buttons button > span.oi-arrow-right").toHaveCount(1, {
            message: "The next button should be there",
        });
        expect(".o_view_scale_selector").toHaveCount(1);
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Day", {
            message: "The default active range should be the first one define in the grid view",
        });
        await contains(".scale_button_selection").click();
        expect(".o-dropdown--menu .o_scale_button_day").toHaveCount(1, {
            message: "The Day scale should be in the dropdown menu",
        });
        expect(".o-dropdown--menu .o_scale_button_week").toHaveCount(1, {
            message: "The week scale should be in the dropdown menu",
        });
        expect(".o-dropdown--menu .o_scale_button_month").toHaveCount(1, {
            message: "The month scale should be in the dropdown menu",
        });
        expect(".o_grid_column_title.fw-bolder").toHaveCount(1, {
            message: "The column title containing the date should be the current date",
        });
        expect(".o_grid_column_title.fw-bolder").toHaveText("Mon,\nJan 30", {
            message: "The current date should be Monday on 30 January 2023",
        });
        expect(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)").toHaveCount(
            1,
            {
                message: "It should have 1 column",
            }
        );
        expect(".o_grid_column_title.o_grid_row_total").toHaveCount(1, {
            message: "It should have 1 column for the total",
        });
        expect(".o_grid_column_title.o_grid_row_total").toHaveCount(1);
        expect(".o_grid_column_title.o_grid_row_total").toHaveText("Unit Amount", {
            message: "The column title of row totals should be the string of the measure field",
        });

        expect(".o_grid_add_line a").toHaveCount(0, {
            message:
                "No Add a line button should be displayed when create_inline is false (default behavior)",
        });
    });

    test("basic empty grid view using a specific range by default", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
            domain: Domain.FALSE.toList({}),
        });

        expect(".o_grid_view").toHaveCount(1);
        expect(".o_grid_renderer").toHaveCount(1);
        expect(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)").toHaveCount(
            7,
            {
                message: "It should have 7 column representing the dates on a week.",
            }
        );
        expect(
            queryAllTexts(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)")
        ).toEqual(
            [
                "Sun,\nJan 29",
                "Mon,\nJan 30",
                "Tue,\nJan 31",
                "Wed,\nFeb 1",
                "Thu,\nFeb 2",
                "Fri,\nFeb 3",
                "Sat,\nFeb 4",
            ],
            { message: "check the columns title is correctly formatted when the range is week" }
        );
        expect(".o_grid_column_title.o_grid_row_total").toHaveCount(1, {
            message: "It should have 1 column for the total",
        });
        expect(".o_grid_column_title.fw-bolder").toHaveCount(1, {
            message: "The column title containing the current date should not be there.",
        });
        expect(".o_grid_column_title.fw-bolder").toHaveText("Mon,\nJan 30", {
            message: "The current date should be Monday on 30 January",
        });
    });

    test("basic grid view", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        expect(
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveCount(14, {
            message:
                "The number of cells containing numeric value and whom is not a total cell should be 14 (2 rows and 7 cells to represent the week)",
        });
        expect(
            ".o_grid_row.o_grid_highlightable.text-danger:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveCount(1, {
            message: "In those 14 cells, one has a value less than 0 and so the text should be red",
        });
        expect(
            ".o_grid_row.o_grid_highlightable.text-danger:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveText("-3.50", {
            message: "The cell with text color in red should contain `-3.50`",
        });
        expect(".o_grid_row.o_grid_highlightable.o_grid_column_total.text-danger").toHaveCount(1, {
            message:
                "The cell containing the column total and in that column a cell is negative to also get a total negative should have text color in red",
        });
        expect(".o_grid_row.o_grid_highlightable.o_grid_column_total.text-danger").toHaveText(
            "-3.50"
        );
        expect(".o_grid_row.o_grid_highlightable.o_grid_row_total.bg-danger").toHaveCount(1);
        expect(".o_grid_row.o_grid_highlightable.o_grid_row_total.bg-danger").toHaveText("-3.50");
        expect(".o_grid_row.o_grid_highlightable > div.bg-info").toHaveCount(3, {
            message:
                "The cell in the column of the current should have `bg-info` class as the header",
        });
        expect(".o_grid_row.o_grid_row_title.o_grid_highlightable").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row.o_grid_row_title.o_grid_highlightable")).toEqual([
            "P1\n|\nBS task",
            "Webocalypse Now\n|\nAnother BS task",
        ]);
        await contains(".o_grid_navigation_buttons button span.oi-arrow-right").click();
        expect(
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveCount(0, {
            message: "No cell should be found because no records is found next week",
        });
        expect(".o_view_nocontent").toHaveCount(1, {
            message: "No content div should be displayed",
        });
        expect("div.bg-info").toHaveCount(0, {
            message: "No column should be the current date since we move in the following week.",
        });
        await contains(".o_grid_navigation_buttons button span.oi-arrow-right").click();
        expect("div.o_grid_row_title").toHaveCount(0, { message: "should not have any cell" });
    });

    test("basic grouped grid view", async () => {
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });

        expect(".o_grid_section.o_grid_section_title").toHaveCount(1, {
            message: "A section should be displayed (for the project P1)",
        });
        expect(".o_grid_section.o_grid_section_title").toHaveText("P1", {
            message: "The title of the section should be the project name",
        });
        expect(".o_grid_section:not(.o_grid_section_title, .o_grid_row_total)").toHaveCount(7, {
            message:
                "7 cells for the section should be displayed to represent the total per day of the section",
        });
        expect(".o_grid_section.o_grid_row_total").toHaveCount(1, {
            message:
                "One cell should be displayed to display the total of the week for the whole section",
        });
        expect(".o_grid_section.o_grid_row_total").toHaveText("10:00", {
            message: "The total of the section should be equal to 10 hours.",
        });
        expect(".o_grid_row.o_grid_row_title").toHaveCount(2, {
            message: "2 rows should be displayed below that section (one per task)",
        });
        expect(queryAllTexts(".o_grid_row.o_grid_row_title")).toEqual(["None", "BS task"]);
        expect(
            ".o_grid_row:not(.o_grid_row_title,.o_grid_row_total,.o_grid_column_total,.o_grid_add_line)"
        ).toHaveCount(14, {
            message: "7 cells per row should be displayed to get value per day in the current week",
        });
        expect(
            queryAllTexts(
                ".o_grid_row:not(.o_grid_row_title,.o_grid_row_total,.o_grid_column_total,.o_grid_add_line)"
            )
        ).toEqual([
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
        ]);
        expect(".o_grid_row.o_grid_row_total").toHaveCount(2, {
            message: "One cell per row should be displayed to display the total of the week",
        });
        expect(queryAllTexts(".o_grid_row.o_grid_row_total")).toEqual(["2:30", "7:30"]);
        expect(".o_grid_search_btn").toHaveCount(0, {
            message: "No search button should be displayed in the grid cells.",
        });
        await hover(".o_grid_section.o_grid_highlightable:eq(1)");
        await contains(".o_grid_cell button.o_grid_search_btn").click();

        // Click on next period to have no data
        await contains(".o_grid_navigation_buttons button span.oi-arrow-left").click();
        expect(".o_grid_section").toHaveCount(0);
        expect(
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveCount(0, {
            message: "No cell should be found because no records is found next week",
        });
        expect(".o_view_nocontent").toHaveCount(1, {
            message: "No content div should be displayed",
        });
        expect("div.bg-info").toHaveCount(0, {
            message: "No column should be the current date since we move in the following week.",
        });
    });

    test("clicking on the info icon on a cell triggers a do_action for section rows", async () => {
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });
        expect(".o_grid_search_btn").toHaveCount(0, {
            message: "No search button should be displayed in the grid cells.",
        });
        await hover(".o_grid_section.o_grid_highlightable:eq(1)");
        await contains(".o_grid_cell button.o_grid_search_btn").click();
    });

    test("Add/remove groupbys in search view", async () => {
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        await toggleSearchBarMenu();
        await toggleMenuItem("Task");
        await toggleMenuItem("Project");
        expect(".o_grid_section").toHaveCount(0);
        expect(".o_grid_row_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["None\n|\nP1", "BS task\n|\nP1"]);
        await contains(".o_grid_navigation_buttons button span.oi-arrow-right").click();
        expect(".o_grid_section").toHaveCount(0);
        expect(".o_grid_row_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row_title")).toEqual([
            "BS task\n|\nP1",
            "Another BS task\n|\nWebocalypse Now",
        ]);

        // Remove the group and check the default groupbys defined in the view are correctly used.
        await toggleSearchBarMenu();
        await toggleMenuItem("Task");
        await toggleMenuItem("Project");
        expect(".o_grid_section_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_section_title")).toEqual(["P1", "Webocalypse Now"]);
        expect(".o_grid_row_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["BS task", "Another BS task"]);
    });

    test("groupBy with a field", async () => {
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        await toggleSearchBarMenu();
        await contains("span.o_menu_item:not(.o_add_custom_filter)").click();
        expect(".o_grid_section").toHaveCount(0);
        expect(".o_grid_row_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["None", "BS task"]);
        await contains(".o_grid_navigation_buttons button span.oi-arrow-right").click();
        expect(".o_grid_section").toHaveCount(0);
        expect(".o_grid_row_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["BS task", "Another BS task"]);
    });

    test("groupBy doesn't change the scale", async () => {
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        await contains(".scale_button_selection").click();
        await contains(".o-dropdown--menu .o_scale_button_month").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Month", {
            message: "The active range should be Month",
        });
        await toggleSearchBarMenu();
        await contains("div.o_group_by_menu > span.o_menu_item").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Month", {
            message: "The active range should still be Month",
        });
    });

    test("groupBy with column field should not be supported", async () => {
        expect.assertions(7);
        mockDate("2017-01-25 00:00:00");
        onRpc("web_read_group", ({ kwargs }) => {
            expect(kwargs.groupby).toEqual(["date:day", "task_id", "project_id"]);
        });
        mockService("notification", {
            add: (message, options) => {
                expect(message).toBe(
                    "Grouping by the field used in the column of the grid view is not possible."
                );
                expect(options.type).toBe("warning");
            },
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        await toggleSearchBarMenu();
        await toggleMenuItem("Date");
        const dateOptionNodes = queryAll(".o_item_option");
        await contains(dateOptionNodes[0]).click();
        await contains(dateOptionNodes[1]).click();
    });

    test("DOM keys are unique", async () => {
        Line._records = [
            { id: 1, project_id: 31, date: "2017-01-24", unit_amount: 2.5 },
            { id: 3, project_id: 143, date: "2017-01-25", unit_amount: 5.5 },
            { id: 2, project_id: 33, date: "2017-01-25", unit_amount: 2 },
            { id: 4, project_id: 143, date: "2017-01-18", unit_amount: 0 },
            { id: 5, project_id: 142, date: "2017-01-18", unit_amount: 0 },
            { id: 10, project_id: 31, date: "2017-01-18", unit_amount: 0 },
            { id: 12, project_id: 142, date: "2017-01-17", unit_amount: 0 },
            { id: 22, project_id: 33, date: "2017-01-19", unit_amount: 0 },
            { id: 21, project_id: 99, date: "2017-01-19", unit_amount: 0 },
        ];
        Project._records = [
            { id: 31, name: "Rem" },
            { id: 33, name: "Rer" },
            { id: 99, name: "Sar" },
            { id: 142, name: "Sas" },
            { id: 143, name: "Sassy" },
        ];
        mockDate("2017-01-25 00:00:00");

        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        expect(queryAllTexts(".o_grid_row_title")).toEqual(["Rem", "Rer", "Sassy"]);
        await contains(".o_grid_navigation_buttons button span.oi-arrow-left").click();
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["Sas", "Rem", "Sassy", "Rer", "Sar"]);
    });

    test("Group By Selection field", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                <field name="selection_field" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                    <range name="year" string="Year" span="year" step="month"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
        });

        expect(queryAllTexts(".o_grid_row_title")).toEqual(["DEF", "GHI"]);
        await contains(".o_grid_navigation_buttons button span.oi-arrow-left").click();
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["ABC", "DEF"]);
    });

    test("Create record with Add button in grid view", async () => {
        mockDate("2017-02-25 00:00:00");

        onRpc("create", (args) => {
            expect(args.args[0][0].date).toBe("2017-02-25", {
                message: "default date should be the current day",
            });
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        expect(".o_grid_row_title").toHaveCount(0);
        expect(".modal").toHaveCount(0);
        expect(".o_view_nocontent").toHaveCount(0);
        await contains(".o_grid_button_add").click();
        expect(".modal").toHaveCount(1);
        await selectFieldDropdownItem("project_id", "P1");
        await selectFieldDropdownItem("task_id", "BS task");

        // input unit_amount
        await contains(".modal .o_field_widget[name=unit_amount] input").edit("4");

        // save
        await contains(".modal .modal-footer button.o_form_button_save").click();

        expect(".o_grid_row_title").toHaveCount(1, {
            message: "the record should be created and a row should be added",
        });
        expect(".o_grid_row_title").toHaveText("P1\n|\nBS task");
    });

    test("Create record with Add button in grid view grouped", async () => {
        mockDate("2017-02-25 00:00:00");

        onRpc("create", (args) => {
            expect(args.args[0][0].date).toBe("2017-02-25", {
                message: "default date should be the current day",
            });
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        expect(".o_grid_row_title").toHaveCount(0);
        expect(".modal").toHaveCount(0);
        expect(".o_view_nocontent").toHaveCount(0);
        await contains(".o_grid_button_add").click();
        expect(".modal").toHaveCount(1);
        await selectFieldDropdownItem("project_id", "P1");
        await selectFieldDropdownItem("task_id", "BS task");

        // input unit_amount
        await contains(".modal .o_field_widget[name=unit_amount] input").edit("4");

        // save
        await contains(".modal .modal-footer button.o_form_button_save").click();

        expect(".o_grid_section_title").toHaveCount(1, {
            message: "the record should be created and a row should be added",
        });
        expect(".o_grid_section_title").toHaveText("P1");
        expect(".o_grid_row_title").toHaveCount(1, {
            message: "the record should be created and a row should be added",
        });
        expect(".o_grid_row_title").toHaveText("BS task");
    });

    test("switching active range", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
        });

        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Week", {
            message: "The default active range should be the first one define in the grid view",
        });
        expect(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total").toHaveCount(
            7,
            {
                message: "It should have 7 columns (one for each day)",
            }
        );
        await contains(".scale_button_selection").click();
        expect(".o-dropdown--menu .o_scale_button_week").toHaveCount(1, {
            message: "The week scale should be in the dropdown menu",
        });
        expect(".o-dropdown--menu .o_scale_button_month").toHaveCount(1, {
            message: "The month scale should be in the dropdown menu",
        });
        await contains(".o-dropdown--menu .o_scale_button_month").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Month", {
            message: "The active range should be Month",
        });
        expect(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)").toHaveCount(
            31,
            {
                message: "It should have 31 columns (one for each day)",
            }
        );
    });

    test("clicking on the info icon on a cell triggers a do_action", async () => {
        onRpc("get_views", (args) => {
            if (args.kwargs.views.find((v) => v[1] === "list")) {
                const context = args.kwargs.context;
                const expectedContext = {
                    default_project_id: 31,
                    default_task_id: 1,
                    default_date: "2017-01-30",
                };
                for (const [key, value] of Object.entries(expectedContext)) {
                    expect(context[key]).toBe(value);
                }
            }
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
        });

        expect(".o_grid_search_btn").toHaveCount(0, {
            message: "No search button should be displayed in the grid cells.",
        });
        await hover(".o_grid_row .o_grid_cell_readonly:eq(1)");
        await contains(".o_grid_cell button.o_grid_search_btn").click();
    });

    test("editing a value", async () => {
        onRpc("grid_update_cell", (args) => {
            expect(args.model).toBe("analytic.line", {
                message: "The update cell should be called in the current model.",
            });
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
            expect(domain).toEqual(domainExpected);
            expect(fieldName).toBe("unit_amount", {
                message: "The value updated should be the measure field",
            });
            expect(value).toBe(2, {
                message: "The value should be the one entered by the user, that is 2",
            });
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });
        const cell = queryFirst(".o_grid_row .o_grid_cell_readonly");
        const cellContainer = cell.closest(".o_grid_highlightable");
        const columnTotal = queryOne(
            `.o_grid_row.o_grid_column_total[data-grid-column="${cellContainer.dataset.gridColumn}"]`
        );
        const [columnTotalHours, columnTotalMinutes] = (
            (columnTotal.textContent?.length && columnTotal.textContent.split(":")) || [0, 0]
        ).map((value) => Number(value));
        const rowTotal = queryOne(
            `.o_grid_row_total[data-grid-row="${cellContainer.dataset.gridRow}"]`
        );
        const [rowTotalHours, rowTotalMinutes] = (
            (rowTotal.textContent?.length && rowTotal.textContent.split(":")) || [0, 0]
        ).map((value) => Number(value));
        expect(cell).toHaveText("0:00");
        await hover(cell);
        await runAllTimers();
        expect(".o_grid_cell").toHaveCount(1, {
            message: "The GridCell component should be mounted on the grid cell hovered.",
        });
        const gridCellComponentEl = queryFirst(".o_grid_cell");
        const gridCell = cell.closest(".o_grid_row");
        expect(gridCellComponentEl.style["grid-row"]).toBe(gridCell.style["grid-row"], {
            message:
                "The GridCell component should be mounted in the same cell than the one hovered in the grid view.",
        });
        expect(gridCellComponentEl.style["grid-column"]).toBe(gridCell.style["grid-column"], {
            message:
                "The GridCell component should be mounted in the same cell than the one hovered in the grid view.",
        });
        expect(gridCellComponentEl.style["z-index"]).toBe("1", {
            message:
                "The GridCell component should be mounted in the same cell than the one hovered in the grid view.",
        });
        await contains(".o_grid_cell").click();
        await animationFrame();
        expect(".o_grid_cell input").toHaveCount(1);
        await contains(".o_grid_cell input").edit("2");
        await animationFrame();
        expect(cell).toHaveText("2:00");
        expect(columnTotal).toHaveText(
            `${columnTotalHours + 2}:${String(columnTotalMinutes).padStart(2, "0")}`
        );
        expect(rowTotal).toHaveText(
            `${rowTotalHours + 2}:${String(rowTotalMinutes).padStart(2, "0")}`
        );
    });

    test("edit grid cell with action context defined", async () => {
        onRpc("grid_update_cell", (args) => {
            const context = args.kwargs.context;
            expect.step("grid_update_cell");
            // the project in the action context should be replaced by the project linked to the grid cell altered
            expect(context.default_project_id).toBe(31);
            expect(context.default_selection_field).toBe("abc");
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
            context: {
                default_project_id: 1,
                default_selection_field: "abc",
            },
        });

        await hover(".o_grid_row .o_grid_cell_readonly");
        await runAllTimers();
        await contains(".o_grid_cell").click();
        await animationFrame();
        expect(".o_grid_cell input").toHaveCount(1);
        await contains(".o_grid_cell input").edit("2");
        expect.verifySteps(["grid_update_cell"]);
    });

    test("hide row total", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid hide_line_total="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });

        expect(".o_grid_row_title").toHaveCount(2);
        expect(".o_grid_row_total").toHaveCount(0, { message: "No row total should be displayed" });
        expect(".o_grid_column_total").toHaveCount(7, {
            message: "Columns total should be displayed",
        });
    });

    test("hide column total", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid hide_column_total="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });

        expect(".o_grid_row_title").toHaveCount(2);
        expect(".o_grid_row_total").toHaveCount(3, { message: "Rows total should be displayed" });
        expect(".o_grid_column_total").toHaveCount(0, {
            message: " No column total should be displayed",
        });
    });

    test("display bar chart total", async () => {
        Line._records.push({
            id: 8,
            project_id: 142,
            task_id: 54,
            date: "2017-01-25",
            unit_amount: 4,
        });
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid barchart_total="1" editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });

        expect(".o_grid_row_title").toHaveCount(3);
        expect(".o_grid_row_total").toHaveCount(5, { message: "Rows total should be displayed" });
        expect(".o_grid_column_total:not(.o_grid_bar_chart_container)").toHaveCount(8, {
            message: "8 cells should be visible to display the total per colunm",
        });
        expect(".o_grid_bar_chart_container").toHaveCount(7, {
            message: "The bar chart total container should be displayed (one per column)",
        });
        expect(".o_grid_bar_chart_total_pill").toHaveCount(2, {
            message:
                "2 bar charts totals should be displayed because the 5 others columns as a total equals to 0.",
        });

        expect(queryAllTexts(".o_grid_bar_chart_total_pill")).toEqual(["", ""]);

        const cell = queryFirst(".o_grid_row .o_grid_cell_readonly");
        expect(cell).toHaveText("0:00");
        await hover(cell);
        await contains(".o_grid_cell").click();
        await animationFrame();
        expect(".o_grid_cell input").toHaveCount(1);
        await contains(".o_grid_cell input").edit("2");
        expect(".o_grid_bar_chart_total_pill").toHaveCount(3, {
            message:
                "3 bar chart totals should be now displayed because a new column as a total greater than 0.",
        });
    });

    test("row and column are highlighted when hovering a cell", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid barchart_total="1" editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });

        expect(".o_grid_row.o_grid_highlightable.bg-700").toHaveCount(0, {
            message: "No cell should be highlighted",
        });
        await hover(".o_grid_row .o_grid_cell_readonly");
        await runAllTimers();
        expect(
            ".o_grid_row.o_grid_highlightable.o_grid_highlighted.o_grid_row_highlighted"
        ).toHaveCount(8, {
            message:
                "8 cells should be highlighted (the cells in the same rows (title row included))",
        });
        expect(".o_grid_row_total.o_grid_highlighted.o_grid_row_highlighted").toHaveCount(1, {
            message: "The row total should also be highlighted",
        });
    });

    test("grid_anchor stays when navigating", async () => {
        // create an action manager to test the interactions with the search view
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
            context: {
                search_default_project_id: 31,
                grid_anchor: "2017-01-31",
            },
        });

        // check first column header
        expect(queryAllTexts(".o_grid_column_title")).toEqual([
            "Today\nWeek",
            "Sun,\nJan 29",
            "Mon,\nJan 30",
            "Tue,\nJan 31",
            "Wed,\nFeb 1",
            "Thu,\nFeb 2",
            "Fri,\nFeb 3",
            "Sat,\nFeb 4",
            "Unit Amount",
        ]);

        // move to previous week, and check first column header
        await contains(".oi-arrow-left").click();
        // check first column header
        expect(queryAllTexts(".o_grid_column_title")).toEqual([
            "Today\nWeek",
            "Sun,\nJan 22",
            "Mon,\nJan 23",
            "Tue,\nJan 24",
            "Wed,\nJan 25",
            "Thu,\nJan 26",
            "Fri,\nJan 27",
            "Sat,\nJan 28",
            "Unit Amount",
        ]);

        // remove the filter in the searchview
        await contains(".o_facet_remove").click();
        expect(queryAllTexts(".o_grid_column_title")).toEqual([
            "Today\nWeek",
            "Sun,\nJan 22",
            "Mon,\nJan 23",
            "Tue,\nJan 24",
            "Wed,\nJan 25",
            "Thu,\nJan 26",
            "Fri,\nJan 27",
            "Sat,\nJan 28",
            "Unit Amount",
        ]);
    });

    test("dialog should not close when clicking the link to many2one field", async () => {
        // create an action manager to test the interactions with the search view
        onRpc("task", "get_formview_id", () => false);
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
        });

        await contains(".o_grid_button_add").click();
        await animationFrame();
        expect(".modal[role='dialog']").toHaveCount(1);

        await selectFieldDropdownItem("task_id", "BS task");
        await contains('.modal .o_field_widget[name="task_id"] button.o_external_button').click();
        // Clicking somewhere on the form dialog should not close it
        expect(".modal[role='dialog']").toHaveCount(2);
        await contains(".modal[role='dialog']").click();
        expect(".modal[role='dialog']").toHaveCount(2);
    });

    test("grid with two tasks with same name, and widget", async () => {
        Task._records = [
            { id: 1, name: "Awesome task", project_id: 31 },
            { id: 2, name: "Awesome task", project_id: 31 },
        ];
        Line._records = [
            { id: 1, task_id: 1, date: "2017-01-30", unit_amount: 2 },
            { id: 2, task_id: 2, date: "2017-01-31", unit_amount: 5.5 },
        ];
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
            context: { search_default_groupby_task: 1 }, // to avoid creating a new grid view to remove project_id in rows
        });

        expect(".o_grid_row_title").toHaveCount(2);
        expect(queryAllTexts(".o_grid_row_title")).toEqual(["Awesome task", "Awesome task"]);
    });

    test("test grid cell formatting with float_time widget", async () => {
        mockDate("2017-01-24 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            groupBy: ["task_id", "project_id"],
            arch: `<grid>
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });

        expect(
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveCount(1);
        expect(
            ".o_grid_row.o_grid_highlightable:not(.o_grid_row_title,.o_grid_column_total,.o_grid_row_total)"
        ).toHaveText("2:30", { message: "Check if the cell is correctly formatted as float time" });
        expect(
            ".o_grid_column_total:not(.o_grid_row_title,.o_grid_row_total,.o_grid_bar_chart_container)"
        ).toHaveCount(1);
        expect(
            ".o_grid_column_total:not(.o_grid_row_title,.o_grid_row_total,.o_grid_bar_chart_container) span"
        ).toHaveText("2:30", { message: "check format time is used" });
        expect(".o_grid_row.o_grid_highlightable.o_grid_row_total").toHaveCount(1);
        expect(".o_grid_row.o_grid_highlightable.o_grid_row_total").toHaveText("2:30", {
            message: "check format time is used",
        });
    });

    test("The help content is not displayed instead of the grid with `display_empty` is true in the grid tag", async () => {
        mockDate("2022-01-01 00:00:00"); // to be sure no data is found
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid display_empty="1">
                    <field name="project_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });

        expect(".o_view_nocontent").toHaveCount(0, {
            message: "No content div should be displayed",
        });
    });

    test("Test add a line in the grid view", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid create_inline="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });

        expect(".o_grid_button_add:visible").toHaveCount(1, {
            message: "'Add a line' control panel button should be visible",
        });
        expect(queryAllTexts(".o_grid_renderer .o_grid_add_line a")).toEqual(["Add a line"], {
            message: "A button `Add a line` should be displayed in the grid view",
        });
        await contains(".o_grid_renderer .o_grid_add_line a").click();
        expect(".modal").toHaveCount(1);
        await contains(".modal .modal-footer button.o_form_button_cancel").click();
        await contains(".o_grid_navigation_buttons button span.oi-arrow-right").click();
        expect(".o_grid_button_add:visible").toHaveCount(1, {
            message: "'Add a line' control panel button should be visible",
        });
    });

    test("create/edit disabled for readonly grid view", async () => {
        Line._fields.validated = fields.Boolean({
            string: "Validation",
            aggregator: "bool_or",
        });
        Line._records.push({
            id: 8,
            project_id: 142,
            task_id: 54,
            date: "2017-01-25",
            unit_amount: 4,
            validated: true,
        });
        mockDate("2017-01-25 00:00:00");
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });
        await hover(".o_grid_row .o_grid_cell_readonly");
        await runAllTimers();
        expect(".o_grid_cell .o_grid_search_btn").toHaveCount(1);
        expect(".o_grid_cell.o_field_cursor_disabled").toHaveCount(0, {
            message: "The cell should not be in readonly",
        });
        await hover(".o_grid_row .o_grid_cell_readonly:eq(1)");
        await runAllTimers();
        expect(".o_grid_cell .o_grid_search_btn").toHaveCount(1);
        expect(".o_grid_cell.o_field_cursor_disabled").toHaveCount(1, {
            message:
                "The cell should be in readonly since at least one timesheet is validated in that cell",
        });
        await contains("button.o_grid_search_btn").click();
    });

    test("display the empty grid without None line when there is no data", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            domain: Domain.FALSE.toList({}),
        });

        expect(".o_grid_section_title").toHaveCount(0, {
            message: "No section should be displayed to display 'None'",
        });
        expect(".o_grid_row_title").toHaveCount(0, {
            message: "No row should be added to display 'None'",
        });
    });

    test('ensure the "None" is displayed in multi-level groupby', async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
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

        expect(".o_grid_section").toHaveCount(0, {
            message:
                "No section should be displayed since the section field is not first in the groupby",
        });
        expect(".o_grid_row_title:eq(0)").toHaveText("None\n|\nABC", {
            message: "'None' should be displayed",
        });
    });

    test("Group By selection field without passing selection field in data", async () => {
        Line._records.push({
            id: 6,
            project_id: 142,
            task_id: 12,
            date: "2017-01-24",
            unit_amount: 7.0,
        });

        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[1, "grid"]],
            context: {
                search_default_groupby_selection: 1,
                grid_anchor: "2017-01-24",
            },
        });

        expect(".o_grid_row_title:contains(None)").toHaveCount(1, {
            message: "'None' should be displayed.",
        });
    });

    test("stop edition when the user clicks outside", async () => {
        const arch = Line._views["grid"].replace("<grid>", '<grid editable="1">');
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch,
        });

        await hover(".o_grid_row .o_grid_cell_readonly:eq(1)");
        await contains(".o_grid_cell").click();
        await animationFrame();

        expect(".o_grid_cell input").toHaveCount(1, { message: "The cell should be in edit mode" });

        await contains(".o_grid_view").click();
        expect(".o_grid_cell input").toHaveCount(0, {
            message: "The GridCell should no longer be visible and so no cell is in edit mode.",
        });
    });

    test("display no content helper when no data and sample data is used (with display_empty='1')", async () => {
        const arch = Line._views["grid"].replace(
            "<grid>",
            `<grid create_inline="1"
                    form_view_id="%(timesheet_grid.my_timesheet_form_view)d"
                    editable="1"
                    display_empty="1"
                    sample="1"
                >`
        );

        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch,
            domain: Domain.FALSE.toList({}),
        });

        expect(".o_view_sample_data").toHaveCount(1, {
            message: "The sample data should be displayed since no records is found.",
        });
        expect(".o_view_nocontent").toHaveCount(1, {
            message:
                "The action helper should also be displayed since the sample data is displayed even if display_empty='1'.",
        });

        expect(".o_grid_buttons .o_grid_button_add:visible").toHaveCount(1, {
            message:
                "The `Add a Line` button should be displayed when no content data is displayed to be able to create a record.",
        });

        await contains(".o_grid_navigation_buttons span.oi-arrow-right").click();
        expect(".o_view_sample_data").toHaveCount(0, {
            message:
                "The sample data should no longer be displayed since display_empty is true in the grid view",
        });
        expect(".o_view_nocontent").toHaveCount(0, {
            message:
                "The no content helper should no longer be displayed since display_empty is true in the grid view.",
        });
        expect(".o_grid_buttons .o_grid_button_add:visible").toHaveCount(1, {
            message: "The `Add a Line` button should be displayed near the `Today` one",
        });
        expect(".o_grid_grid .o_grid_row.o_grid_add_line.position-md-sticky").toHaveCount(1, {
            message:
                "The `Add a Line` button should be displayed in the grid view since create_inline='1'",
        });
    });

    test("Only relevant grid rows are rendered with larger recordsets", async () => {
        // Setup: generates 100 new tasks and related analytic lines distributed
        // in all available projects, deterministically based on their ID.
        const { _fields: alFields, _records: analyticLines } = Line;
        const { _records: tasks } = Task;
        const { _records: projects } = Project;
        const selectionValues = alFields.selection_field.selection;
        const today = luxon.DateTime.local().toFormat("yyyy-MM-dd");
        for (let id = 100; id < 200; id++) {
            const projectId = projects[id % projects.length].id;
            tasks.push({
                id,
                name: `BS task #${id}`,
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

        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        /**
         * Returns unique "data-grid-row" attributes to check for rows equality
         * @returns {string[]}
         */
        const getCurrentRows = () => [
            ...new Set([...grid.children].map((el) => el.dataset.gridRow)),
        ];

        const content = queryOne(".o_content");
        const grid = queryOne(".o_grid_grid");
        const firstRow = grid.querySelector(".o_grid_column_title");
        content.style = "height: 600px; overflow: scroll;";

        // This is to ensure that the virtual rows will not be impacted by
        // sub-pixel calculations.
        await scroll(content, { top: 0 });
        await animationFrame();

        const initialRows = getCurrentRows();
        let currentRows = initialRows;

        expect(content.scrollTop).toBe(0, { message: "content should be scrolled to the top" });
        expect(content.offsetHeight).toBe(710, { message: "content should have its height fixed" });
        // ! This next assertion is important: it ensures that the grid rows are
        // ! hard-coded so that the virtual hook can work with it. Adapt this test
        // ! accordingly should the row height change.
        expect(
            grid.clientHeight - firstRow.offsetHeight /* first row is "auto" so we don't count it */
        ).toBe((tasks.length - 1) /* ignore total row */ * 32 /* base grid row height */, {
            message:
                "grid content should be the height of its row height times the amount of records",
        });
        expect(currentRows.length).toBeLessThan(tasks.length, {
            message: "not all rows should be displayed",
        });

        // Scroll to the middle of the grid
        await scroll(content, { top: content.scrollHeight / 2 });
        await animationFrame();
        expect(currentRows).not.toEqual(getCurrentRows(), { message: "rows should be different" });
        expect(getCurrentRows().length).toBeLessThan(tasks.length, {
            message: "not all rows should be displayed",
        });
        currentRows = getCurrentRows();

        // Scroll to the end of the grid
        await scroll(content, { top: content.scrollHeight });
        await animationFrame();

        expect(currentRows).not.toEqual(getCurrentRows(), { message: "rows should be different" });
        expect(getCurrentRows().length).toBeLessThan(tasks.length, {
            message: "not all rows should be displayed",
        });

        // Scroll back to top
        await scroll(content, { top: 0 });
        await animationFrame();

        // FIXME: virtual hook: rows are not exactly the same after scrolling once for some reason
        // expect(getCurrentRows()).toEqual(initialRows, {
        //     message: "rows should be the same as initially",
        // });
    });

    test("Edition navigate with tab/shift+tab and enter key", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });

        function checkGridCellInRightPlace(expectedGridRow, expectedGridColumn) {
            const gridCell = queryOne(".o_grid_cell");
            expect(gridCell.dataset.gridRow).toBe(expectedGridRow);
            expect(gridCell.dataset.gridColumn).toBe(expectedGridColumn);
        }

        const firstCell = queryOne(".o_grid_row[data-row='1'][data-column='0']");
        expect(firstCell.dataset.gridRow).toBe("2");
        expect(firstCell.dataset.gridColumn).toBe("2");
        await hover(firstCell, ".o_grid_cell_readonly");
        await runAllTimers();
        expect(".o_grid_cell").toHaveCount(1, {
            message: "The GridCell component should be mounted on the grid cell hovered.",
        });
        checkGridCellInRightPlace(firstCell.dataset.gridRow, firstCell.dataset.gridColumn);
        await contains(".o_grid_cell").click();
        await animationFrame();

        // Go to the next cell
        await press("tab");
        await animationFrame();
        checkGridCellInRightPlace("2", "3");

        // Go to the previous cell
        await press("shift+tab");
        await animationFrame();
        checkGridCellInRightPlace("2", "2");

        // Go the cell below
        await press("enter");
        await animationFrame();
        checkGridCellInRightPlace("3", "2");

        // Go up since it is the cell in the row
        await press("enter");
        await animationFrame();
        checkGridCellInRightPlace("2", "3");

        await press("shift+tab");
        await animationFrame();
        checkGridCellInRightPlace("2", "2");

        // Go to the last editable cell in the grid view since it is the first cell.
        await press("shift+tab");
        await animationFrame();
        checkGridCellInRightPlace("3", "8");

        // Go back to the first cell since it is the last cell in grid view.
        await press("tab");
        await animationFrame();
        checkGridCellInRightPlace("2", "2");

        // Go to the last editable cell in the grid view since it is the first cell.
        await press("shift+tab");
        await animationFrame();
        checkGridCellInRightPlace("3", "8");

        // Go back to the first cell since it is the last cell in grid view.
        await press("enter");
        await animationFrame();
        checkGridCellInRightPlace("2", "2");
    });

    test("Add custom buttons in grid view", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });

        expect("button[name='action_test']").toHaveCount(1, {
            message: "The custom button should be visible",
        });
        expect("button[name='action_test_invisible']").toHaveCount(0);
    });

    test("date should be grouped by month in year range", async () => {
        expect.assertions(1);

        onRpc("web_read_group", (args) => {
            expect(args.kwargs.groupby).toEqual(["date:month", "project_id", "task_id"]);
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
        });
    });

    test("columns getter: weekends hidden in 'month' range", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="month" string="Month" span="month" step="day"/>
                    <range name="year" string="Year" span="Year" step="month"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });
        await contains(".scale_button_selection").click();
        await contains(".o_show_weekends").click();
        await animationFrame();

        function getColumnHeaders() {
            return Array.from(document.querySelectorAll(".o_grid_column_title")).map((el) =>
                el.textContent.trim()
            );
        }

        function hasWeekend(dateLabels) {
            return dateLabels.some((text) => text.includes("Sat") || text.includes("Sun"));
        }

        // By default, it's "month"
        let headers = getColumnHeaders();
        expect(hasWeekend(headers)).toBe(false);

        // Switch to "year"
        await contains(".scale_button_selection").click();
        await contains(".o_scale_button_year").click();
        await animationFrame();
        headers = getColumnHeaders();
        expect(headers.length).toBe(14);
    });

    test("range step should correctly be taken into account to load data", async () => {
        expect.assertions(8 + 7);

        let rangeStep = "day";
        onRpc("web_read_group", (args) => {
            expect(args.kwargs.groupby).toEqual([`date:${rangeStep}`, "project_id", "task_id"]);
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `
                <grid display_empty="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                        <range name="day2" string="Day2" span="day" step="month"/>
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="week2" string="Week2" span="week" step="month"/>
                        <range name="month" string="Month" span="month" step="day"/>
                        <range name="month2" string="Month2" span="month" step="month"/>
                        <range name="year" string="Year" span="year" step="day"/>
                        <range name="year2" string="Year2" span="year" step="month"/>
                    </field>
                    <field name="unit_amount" type="measure"/>
                </grid>
            `,
        });
        await contains(".scale_button_selection").click();
        rangeStep = "month";
        await contains(".o-dropdown--menu .o_scale_button_day2").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Day2", {
            message: "The active range should be Day2",
        });
        await contains(".scale_button_selection").click();
        rangeStep = "day";
        await contains(".o-dropdown--menu .o_scale_button_week").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Week", {
            message: "The active range should be Week",
        });
        await contains(".scale_button_selection").click();
        rangeStep = "month";
        await contains(".o-dropdown--menu .o_scale_button_week2").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Week2", {
            message: "The active range should be Week2",
        });
        await contains(".scale_button_selection").click();
        rangeStep = "day";
        await contains(".o-dropdown--menu .o_scale_button_month").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Month", {
            message: "The active range should be Month",
        });
        await contains(".scale_button_selection").click();
        rangeStep = "month";
        await contains(".o-dropdown--menu .o_scale_button_month2").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Month2", {
            message: "The active range should be Month2",
        });
        await contains(".scale_button_selection").click();
        rangeStep = "day";
        await contains(".o-dropdown--menu .o_scale_button_year").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Year", {
            message: "The active range should be year",
        });
        await contains(".scale_button_selection").click();
        rangeStep = "month";
        await contains(".o-dropdown--menu .o_scale_button_year2").click();
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Year2", {
            message: "The active range should be year2",
        });
    });

    test("display notification when the update of the grid cell cannot be done", async () => {
        onRpc("grid_update_cell", () => {
            expect.step("grid_update_cell");
            return {
                type: "ir.actions.client",
                tag: "display_notification",
                params: {
                    message: "test display a notification",
                    type: "danger",
                    sticky: false,
                },
            };
        });
        mockService("action", {
            doAction: (data) => {
                if (data.tag === "display_notification") {
                    expect.step(`notification_${data.params.type}`);
                }
            },
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid editable="1">
                <field name="project_id" type="row"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`,
        });

        await hover(".o_grid_row .o_grid_cell_readonly");
        await runAllTimers();
        await contains(".o_grid_cell").click();
        await animationFrame();
        expect(".o_grid_cell input").toHaveCount(1);
        await contains(".o_grid_cell input").edit("2");
        expect.verifySteps(["grid_update_cell", "notification_danger"]);
    });

    test("today should be focused", async () => {
        expect.assertions(7);
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `
                <grid display_empty="1" editable="1">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure"/>
                </grid>
            `,
        });

        const content = queryOne(".o_content");
        content.style.overflow = "scroll";
        function expectScrollLeft(shouldBeScrolled) {
            if (shouldBeScrolled) {
                expect(content.scrollLeft).toBeGreaterThan(0);
                content.scrollLeft = 0;
            } else {
                expect(content.scrollLeft).toBe(0);
            }
        }

        await contains("button.btn-secondary[data-hotkey='v']").click();
        await animationFrame();
        await contains("span.dropdown-item[data-hotkey='m']").click();
        expectScrollLeft(true);

        await contains("button.btn-secondary[data-hotkey='n']").click();
        expectScrollLeft(false);

        await contains("button.btn-secondary[data-hotkey='p']").click();
        expectScrollLeft(true);

        await contains("button.btn-secondary[data-hotkey='p']").click();
        expectScrollLeft(false);

        await contains("button.btn-secondary[data-hotkey='t']").click();
        expectScrollLeft(true);

        await hover(".o_grid_highlightable:not(.o_grid_column_title):not(.o_grid_row_title)");
        await contains(".o_grid_cell").click();
        await animationFrame();
        await contains(".o_grid_cell input").edit("2");
        expectScrollLeft(false);

        await contains("button.btn-secondary[data-hotkey='v']").click();
        await animationFrame();
        await contains("span.dropdown-item[data-hotkey='w']").click();
        expectScrollLeft(false);
    });

    test("grid: show/hide weekend will show/hide grid values", async () => {
        mockDate("2017-01-25 00:00:00");
        patchWithCleanup(browser, {
            localStorage: {
                setItem(key, value) {
                    expect.step(`${key}-${value}`);
                },
                getItem(key) {
                    if (key === "grid.isWeekendVisible") {
                        return true;
                    }
                },
            },
        });
        Line._records.push({
            id: 6,
            project_id: 31,
            task_id: 1,
            selection_field: "def",
            date: "2017-01-22",
            unit_amount: 10,
        });
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });

        expect(".o_grid_section.o_grid_row_total").toHaveText("20:00", {
            message: "should show 20h in timesheet",
        });
        expect(queryAllTexts(".o_grid_row.o_grid_row_total")).toEqual(["17:30", "2:30"]);
        expect(".scale_button_selection").toHaveCount(1);
        await contains(".scale_button_selection").click();
        expect(".o-dropdown--menu span.dropdown-item.active").toHaveCount(2);
        await contains(".o-dropdown--menu span.dropdown-item.active:eq(1)").click();

        expect(".o_grid_section.o_grid_row_total").toHaveText("10:00", {
            message: "should show 10 hours as weekend is hidden",
        });
        expect(queryAllTexts(".o_grid_row.o_grid_row_total")).toEqual(["7:30", "2:30"]);
        expect.verifySteps(["grid.isWeekendVisible-false"]);
    });

    test("grid: use the context in the action when a record will be created", async () => {
        mockDate("2017-02-25 00:00:00");
        onRpc("create", (args) => {
            expect(args.args[0][0].date).toBe("2017-02-25", {
                message: "default date should be the current day",
            });
        });

        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
            context: {
                default_project_id: 31,
            },
        });
        expect(".o_grid_row_title").toHaveCount(0);
        expect(".modal").toHaveCount(0);
        expect(".o_view_nocontent").toHaveCount(0);
        await contains(".o_grid_button_add").click();
        expect(".modal").toHaveCount(1);
        expect(".modal div[name=project_id]").toHaveCount(1);
        expect(".modal div[name=project_id] input").toHaveValue("P1");
    });

    test("restore navigationInfo from previous state", async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
        });
        await contains(".oi-arrow-left").click();
        expect(
            queryAllTexts(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)")
        ).toEqual([
            "Sun,\nJan 22",
            "Mon,\nJan 23",
            "Tue,\nJan 24",
            "Wed,\nJan 25",
            "Thu,\nJan 26",
            "Fri,\nJan 27",
            "Sat,\nJan 28",
        ]);
        await hover(".o_grid_row .o_grid_cell_readonly:eq(0)");
        await runAllTimers();
        await contains(".o_grid_cell button.o_grid_search_btn").click();
        await contains(".breadcrumb-item.o_back_button").click();
        expect(
            queryAllTexts(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)")
        ).toEqual([
            "Sun,\nJan 22",
            "Mon,\nJan 23",
            "Tue,\nJan 24",
            "Wed,\nJan 25",
            "Thu,\nJan 26",
            "Fri,\nJan 27",
            "Sat,\nJan 28",
        ]);
    });

    test("export navigationInfo when col is not a range", async () => {
        Line._views["grid"] = `<grid>
            <field name="project_id" type="row"/>
            <field name="task_id" type="col"/>
            <field name="unit_amount" type="measure" widget="float_time"/>
        </grid>`;
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            res_model: "analytic.line",
            type: "ir.actions.act_window",
            views: [[false, "grid"]],
        });
        await hover(".o_grid_row .o_grid_cell_readonly:eq(0)");
        await contains(".o_grid_cell button.o_grid_search_btn").click();
        expect(".o_list_view").toHaveCount(1);
    });

    test("Scale: scale default is fetched from localStorage", async () => {
        patchWithCleanup(browser.localStorage, {
            getItem(key) {
                if (String(key).startsWith("scaleOf-viewId")) {
                    return "week";
                }
            },
            setItem(key, value) {
                if (key === `scaleOf-viewId-${view.env.config.viewId}`) {
                    expect.step(`scale_${value}`);
                }
            },
        });

        const view = await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: /* xml */ `
            <grid>
                <field name="project_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="year" string="Year" span="year" step="month"/>
                </field>
                <field name="unit_amount" type="measure"/>
            </grid>`,
        });

        expect(".scale_button_selection").toHaveText("Week");
        await contains(".o_view_scale_selector .dropdown-toggle").click();
        await contains(`.o_scale_button_year`).click();
        expect(".scale_button_selection").toHaveText("Year");
        expect.verifySteps(["scale_year"]);
    });
});
describe.tags("mobile");
describe("grid_view_mobile", () => {
    test("basic empty grid view in mobile", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
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
            domain: Domain.FALSE.toList({}),
        });

        expect(".o_grid_view").toHaveCount(1);
        expect(".o_grid_renderer").toHaveCount(1);
        expect(".o_control_panel_main_buttons .o_grid_buttons").toHaveCount(1);
        expect(".o_grid_custom_buttons").toHaveCount(0);
        expect(".o_grid_navigation_buttons").toHaveCount(1);
        expect(".o_grid_navigation_buttons button:eq(0)").toHaveText("Today", {
            message: "The first navigation button should be the Today one.",
        });
        expect(".o_grid_navigation_buttons > div > button > span.oi-arrow-left").toHaveCount(1, {
            message: "The previous button should be there",
        });
        expect(".o_grid_navigation_buttons > div > button > span.oi-arrow-right").toHaveCount(1, {
            message: "The previous button should be there",
        });
        expect(".o_view_scale_selector").toHaveCount(1);
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Day", {
            message: "The default active range should be the first one define in the grid view",
        });
        await contains(".scale_button_selection").click();
        expect(".o-dropdown--menu .o_scale_button_day").toHaveCount(1, {
            message: "The Day scale should be in the dropdown menu",
        });
        expect(".o-dropdown--menu .o_scale_button_week").toHaveCount(1, {
            message: "The week scale should be in the dropdown menu",
        });
        expect(".o-dropdown--menu .o_scale_button_month").toHaveCount(1, {
            message: "The month scale should be in the dropdown menu",
        });
        expect(".o_grid_column_title.fw-bolder").toHaveCount(1, {
            message: "The column title containing the date should be the current date",
        });
        expect(".o_grid_column_title.fw-bolder").toHaveText("Mon,\nJan 30", {
            message: "The current date should be Monday on 30 January 2023",
        });
        expect(".o_grid_column_title:not(.o_grid_navigation_wrap, .o_grid_row_total)").toHaveCount(
            1,
            { message: "It should have 1 column" }
        );
        expect(".o_grid_column_title.o_grid_row_total").toHaveCount(1, {
            message: "It should have 1 column for the total",
        });
        expect(".o_grid_column_title.o_grid_row_total").toHaveCount(1);
        expect(".o_grid_column_title.o_grid_row_total").toHaveText("Unit Amount", {
            message: "The column title of row totals should be the string of the measure field",
        });

        expect(".o_grid_add_line a").toHaveCount(0, {
            message:
                "No Add a line button should be displayed when create_inline is false (default behavior)",
        });
    });

    test("grid view should open in day range for mobile", async () => {
        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `<grid string="Timesheet">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
        });

        expect(".o_view_scale_selector").toHaveCount(1);
        expect(".o_view_scale_selector button.scale_button_selection").toHaveText("Day", {
            message: "The default active range should be the first one define in the grid view",
        });
    });

    test("virtual scroll loads next records on mobile", async () => {
        // Inspired by the test `Only relevant grid rows are rendered with larger recordsets`

        // Setup: generates 100 new tasks and related analytic lines distributed
        // in all available projects, deterministically based on their ID.
        const { _fields: alFields, _records: analyticLines } = Line;
        const { _records: tasks } = Task;
        const { _records: projects } = Project;
        const selectionValues = alFields.selection_field.selection;
        const today = luxon.DateTime.local().toFormat("yyyy-MM-dd");
        for (let id = 100; id < 200; id++) {
            const projectId = projects[id % projects.length].id;
            tasks.push({
                id,
                name: `BS task #${id}`,
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

        await mountView({
            type: "grid",
            resModel: "analytic.line",
            arch: `
                <grid>
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure"/>
                </grid>`,
        });

        const content = queryOne(".o_content");
        content.style = "height: 600px; overflow: scroll;";

        // This is to ensure that the virtual rows will not be impacted by
        // sub-pixel calculations.
        await scroll(content, { top: 0 });
        await animationFrame();

        // Scroll to the middle of the grid
        await scroll(content, { top: content.scrollHeight / 2 });
        await animationFrame();
        expect(`a[href="/odoo/m-task/101"]`).toHaveCount(1);

        // Scroll to the end of the grid
        await scroll(content, { top: content.scrollHeight });
        await animationFrame();
        expect(`a[href="/odoo/m-task/199"]`).toHaveCount(1);
    });
});
