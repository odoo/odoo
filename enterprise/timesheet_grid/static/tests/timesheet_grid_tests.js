/** @odoo-module **/

import { click, getFixture, patchDate, getNodesTextContent } from "@web/../tests/helpers/utils";
import { removeFacet } from "@web/../tests/search/helpers";
import { setupViewRegistries } from "@web/../tests/views/helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";

import { TimesheetGridSetupHelper } from "./helpers";

let serverData, target, timesheetGridSetup;

addModelNamesToFetch(["project.project", "project.task"]);


function assertSectionsColsOverAndDownTime(target, assert) {
    assert.deepEqual(
        getNodesTextContent(target.querySelectorAll(".o_grid_section.text-warning")),
        ["25:00", "10:00"],
        "Mario has overtime 25h > 8h and 10h > 8h"
    );
    assert.containsOnce(
        target,
        ".o_grid_section.o_grid_row_total.text-bg-warning",
        "Mario has overtime 35 > 16"
    );
    assert.deepEqual(
        getNodesTextContent(target.querySelectorAll(".o_grid_section.text-danger")),
        ["2:30", "0:00"],
        "Luigi has downtime 2:30h < 6h and 0h < 6h"
    );
    assert.containsOnce(
        target,
        ".o_grid_section.o_grid_row_total.text-bg-danger",
        "Luigi has downtime 2.30 < 12"
    );
    assert.containsN(
        target,
        ".o_grid_section.o_grid_row_total.text-bg-success",
        2,
        "Yoshi has no overtime (5.5 = 5.5). Same for Toad (0 = 0)"
    );
}

function assertOutOfRangeCells(target, assert, exceptedResult) {
    assert.deepEqual(
        getNodesTextContent(target.querySelectorAll(".o_grid_row.text-danger")),
        exceptedResult,
    );
}

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        timesheetGridSetup = new TimesheetGridSetupHelper();
        const result = await timesheetGridSetup.setupTimesheetGrid();
        serverData = result.serverData;
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("TimesheetGridView");

    QUnit.test("basic timesheet - no groupby", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: [] },
        });

        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one_avatar_employee",
            6,
            "should have 6 employee avatars"
        );
        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one",
            11,
            "should have 11 many2one widgets in total"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            6,
            "should have 6 rows displayed in the grid"
        );
        assertOutOfRangeCells(target, assert, ["-3:30", "25:00"]);
    });

    QUnit.test("basic timesheet - groupby employees", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: ["employee_id"] },
        });

        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one_avatar_employee",
            4,
            "should have 4 employee avatars"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            4,
            "should have 4 rows displayed in the grid"
        );
        assertOutOfRangeCells(target, assert, ["-3:30", "25:00"]);
    });

    QUnit.test("basic timesheet - groupby employees>task", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: ["employee_id", "task_id"] },
        });

        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one_avatar_employee",
            6,
            "should have 6 employee avatars"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            6,
            "should have 6 rows displayed in the grid"
        );
        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one",
            5,
            "should have 5 many2one widgets in total"
        );
        assert.containsN(target, ".o_grid_component", 11, "should have 11 widgets in total");
        assertOutOfRangeCells(target, assert, ["-3:30", "25:00"]);
    });

    QUnit.test("basic timesheet - groupby task>employees", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: ["task_id", "employee_id"] },
        });

        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one_avatar_employee",
            6,
            "should have 6 employee avatars"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            6,
            "should have 4 rows displayed in the grid"
        );
        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one",
            6,
            "should have 6 many2one widgets in total"
        );
        assert.containsOnce(
            target,
            ".o_grid_component_timesheet_many2one .o_grid_no_data",
            "We should have one many2one widget with no data"
        );
        assert.containsN(target, ".o_grid_component", 12, "should have 12 widgets in total");
        assert.containsOnce(
            target,
            ".o_grid_component_timesheet_many2one .o_grid_no_data",
            "should have 1 widget with no data"
        );
        assertOutOfRangeCells(target, assert, ["-3:30"]);
    });

    QUnit.test("timesheet with employee section - no groupby", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[1, "grid"]],
            context: { group_by: [] },
        });

        assert.containsN(
            target,
            ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
            4,
            "should have 4 sections with employee avatar"
        );
        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one",
            11,
            "should have 11 many2one widgets in total"
        );
        assert.containsNone(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one_avatar_employee",
            "No employee avatar should be displayed in the rows"
        );
        assert.containsN(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one",
            11,
            "The 11 many2one widgets should be displayed in the rows"
        );
        assert.containsNone(
            target,
            ".o_grid_section_title .o_grid_component_timesheet_many2one",
            "No many2one widgets should be displayed in the sections"
        );
        assert.containsN(
            target,
            ".o_grid_section_title",
            4,
            "4 sections should be rendered in the grid view"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            6,
            "should have 6 rows displayed in the grid"
        );
        assert.containsN(
            target,
            ".o_grid_add_line .btn-link",
            2,
            "should have 2 Add a line button"
        );
        assertSectionsColsOverAndDownTime(target, assert);
        assertOutOfRangeCells(target, assert, ["-3:30", "25:00"]);
    });

    QUnit.test("timesheet with employee section - groupby employees", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[1, "grid"]],
            context: { group_by: ["employee_id"] },
        });

        assert.containsNone(
            target,
            ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
            "No employee avatar should be displayed in the sections"
        );
        assert.containsN(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one_avatar_employee",
            4,
            "should have 4 rows with employee avatar"
        );
        assert.containsNone(
            target,
            ".o_grid_component_timesheet_many2one",
            "No many2one widgets should be rendered"
        );
        assert.containsNone(
            target,
            ".o_grid_section_title",
            "No sections should be displayed in the grid"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            4,
            "4 rows should be rendered in the grid view"
        );
        assertOutOfRangeCells(target, assert, ["-3:30", "25:00"]);
    });

    QUnit.test("timesheet with employee section - groupby employee>task", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[1, "grid"]],
            context: { group_by: ["employee_id", "task_id"] },
        });

        assert.containsN(
            target,
            ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
            4,
            "should have 4 sections with employee avatar"
        );
        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one",
            6,
            "should have 6 many2one widgets in total"
        );
        assert.containsOnce(
            target,
            ".o_grid_component_timesheet_many2one .o_grid_no_data",
            "We should have one many2one widget with no data"
        );
        assert.containsNone(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one_avatar_employee",
            "No employee avatar should be displayed in the rows"
        );
        assert.containsN(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one",
            6,
            "The 6 many2one widgets should be displayed in the rows"
        );
        assert.containsOnce(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one .o_grid_no_data",
            "We should have one many2one widget with no data"
        );
        assert.containsNone(
            target,
            ".o_grid_section_title .o_grid_component_timesheet_many2one",
            "No many2one widgets should be displayed in the sections"
        );
        assert.containsN(
            target,
            ".o_grid_section_title",
            4,
            "4 sections should be rendered in the grid view"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            6,
            "should have 6 rows displayed in the grid"
        );
        assertSectionsColsOverAndDownTime(target, assert);
        assertOutOfRangeCells(target, assert, ["-3:30", "25:00"]);
    });

    QUnit.test("timesheet with employee section - groupby task>employees", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[1, "grid"]],
            context: { group_by: ["task_id", "employee_id"] },
        });

        assert.containsNone(
            target,
            ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
            "No employee avatar should be displayed in the sections"
        );
        assert.containsN(
            target,
            ".o_grid_row_title .o_grid_component_timesheet_many2one_avatar_employee",
            6,
            "should have 4 rows with employee avatar"
        );
        assert.containsN(
            target,
            ".o_grid_component_timesheet_many2one",
            6,
            "5 many2one widgets should be rendered"
        );
        assert.containsOnce(
            target,
            ".o_grid_component_timesheet_many2one .o_grid_no_data",
            "We should have one many2one widget with no data"
        );
        assert.containsNone(
            target,
            ".o_grid_section_title",
            "No sections should be displayed in the grid"
        );
        assert.containsN(
            target,
            ".o_grid_row_title",
            6,
            "6 rows should be rendered in the grid view"
        );
        assertOutOfRangeCells(target, assert, ["-3:30"]);
    });

    QUnit.test(
        "timesheet avatar widget should not display overtime if in the view show the current period (today is displayed in the period)",
        async function (assert) {
            const { openView } = await start({
                serverData,
                async mockRPC(route, args) {
                    return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
                },
            });

            await openView({
                res_model: "analytic.line",
                views: [[1, "grid"]],
                context: { group_by: [] },
            });

            assert.containsN(
                target,
                ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
                4,
                "should have 4 sections with employee avatar"
            );

            assert.containsNone(
                target,
                ".o_grid_section_title .o_timesheet_overtime_indication",
                "No overtime indication should be displayed"
            );
        }
    );

    QUnit.test(
        "timesheet avatar widget should display hours in gray if all the hours were performed",
        async function (assert) {
            patchDate(2017, 0, 31, 0, 0, 0);
            const { openView } = await start({
                serverData,
                async mockRPC(route, args) {
                    return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
                },
            });

            await openView({
                res_model: "analytic.line",
                views: [[1, "grid"]],
                context: { group_by: [], grid_anchor: "2017-01-25" },
            });

            assert.containsN(
                target,
                ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
                4,
                "should have 4 sections with employee avatar"
            );
            assert.containsN(
                target,
                ".o_grid_section_title .o_timesheet_overtime_indication",
                3,
                "All the avatar should have a timesheet overtime indication displayed except one since he did his working hours without any overtime in the grid"
            );
            const sectionsTitleNodes = target.querySelectorAll(".o_grid_section_title");
            const sectionWithDangerOvertimeTextContents = [];
            const sectionWithSuccessOvertimeTextContents = [];
            const sectionWithoutOvertimeTextContents = [];
            for (const node of sectionsTitleNodes) {
                const overtimeNode = node.querySelector(".o_timesheet_overtime_indication");
                if (overtimeNode) {
                    if (overtimeNode.classList.contains("text-danger")) {
                        sectionWithDangerOvertimeTextContents.push(node.textContent);
                    } else {
                        sectionWithSuccessOvertimeTextContents.push(node.textContent);
                    }
                } else {
                    sectionWithoutOvertimeTextContents.push(node.textContent);
                }
            }
            assert.deepEqual(
                sectionWithDangerOvertimeTextContents,
                ["Mario-198:00", "Toad-1.00"],
                "Mario and Toad have not done all his working hours (the overtime indication for Toad is formatted in float since uom is Days and not hours)"
            );
            assert.deepEqual(
                sectionWithSuccessOvertimeTextContents,
                ["Yoshi+04:00"],
                "Yoshi should have done his working hours and even more."
            );
            assert.deepEqual(
                sectionWithoutOvertimeTextContents,
                ["Luigi"],
                "Luigi should have done his working hours without doing extra hours"
            );
        }
    );

    QUnit.test(
        "employee overtime indication should be displayed in non-working days if timesheet recorded",
        async function (assert) {
            patchDate(2017, 0, 31, 0, 0, 0);
            const { openView } = await start({
                serverData: {
                    ...serverData,
                    views: {
                        ...serverData.views,
                        "analytic.line,2,grid": `<grid js_class="timesheet_grid" barchart_total="1" create_inline="1">
                            <field name="employee_id" type="row" section="1" widget="timesheet_many2one_avatar_employee"/>
                            <field name="project_id" type="row" widget="timesheet_many2one"/>
                            <field name="task_id" type="row" widget="timesheet_many2one"/>
                            <field name="date" type="col">
                                <range name="day" string="Day" span="day" step="day"/>
                            </field>
                            <field name="unit_amount" type="measure" widget="float_time"/>
                        </grid>`,
                    },
                },
                async mockRPC(route, args) {
                    if (args.method === "get_timesheet_and_working_hours_for_employees") {
                        return {
                            1: { units_to_work: 0, uom: "hours", worked_hours: 2 },
                            3: { units_to_work: 8, uom: "hours", worked_hours: 5.5 },
                        };
                    }
                    return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
                },
            });

            await openView({
                res_model: "analytic.line",
                views: [[2, "grid"]],
                context: { group_by: [], grid_anchor: "2017-01-25" },
            });

            assert.containsN(
                target,
                ".o_grid_section_title .o_grid_component_timesheet_many2one_avatar_employee",
                2,
                "should have 4 sections with employee avatar"
            );
            assert.containsN(
                target,
                ".o_grid_section_title .o_timesheet_overtime_indication",
                2,
                "All the avatar should have a timesheet overtime indication displayed except one since he did his working hours without any overtime in the grid"
            );
            const sectionsTitleNodes = target.querySelectorAll(".o_grid_section_title");
            const sectionWithDangerOvertimeTextContents = [];
            const sectionWithSuccessOvertimeTextContents = [];
            const sectionWithoutOvertimeTextContents = [];
            for (const node of sectionsTitleNodes) {
                const overtimeNode = node.querySelector(".o_timesheet_overtime_indication");
                if (overtimeNode) {
                    if (overtimeNode.classList.contains("text-danger")) {
                        sectionWithDangerOvertimeTextContents.push(node.textContent);
                    } else {
                        sectionWithSuccessOvertimeTextContents.push(node.textContent);
                    }
                } else {
                    sectionWithoutOvertimeTextContents.push(node.textContent);
                }
            }
            assert.deepEqual(
                sectionWithDangerOvertimeTextContents,
                ["Yoshi-02:30"],
                "Mario and Toad have not done all his working hours (the overtime indication for Toad is formatted in float since uom is Days and not hours)"
            );
            assert.deepEqual(
                sectionWithSuccessOvertimeTextContents,
                ["Mario+02:00"],
                "Yoshi should have done his working hours and even more."
            );
        }
    );

    QUnit.test("when in Next week date should be first working day", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: [] },
        });

        await click(target, ".o_grid_navigation_buttons > div > button > span.oi-arrow-right");
        await click(target, ".o_control_panel_main_buttons .o_grid_button_add");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=date] input").value,
            "01/30/2017"
        );
    });

    QUnit.test("when in Previous week date should be first working day", async function (assert) {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[false, "grid"]],
            context: { group_by: [] },
        });

        await click(target, ".o_grid_navigation_buttons > div > button > span.oi-arrow-left");
        await click(target, ".o_control_panel_main_buttons .o_grid_button_add");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=date] input").value,
            "01/16/2017"
        );
    });

    QUnit.test("display sample data and then data + fetch last validate timesheet date", async (assert) => {
        serverData.views["analytic.line,1,grid"] = serverData.views["analytic.line,1,grid"].replace("<grid", "<grid sample='1'");

        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "get_last_validated_timesheet_date") {
                    assert.step("get_last_validated_timesheet_date");
                }
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[1, "grid"]],
            context: { search_default_nothing: 1 },
        });
        assert.containsOnce(target, ".o_view_sample_data");
        await removeFacet(target);
        assert.containsNone(target, ".o_grid_sample_data");
        assert.containsN(target, ".o_grid_section_title", 4);
        assert.verifySteps(["get_last_validated_timesheet_date"]); // the rpc should be called only once
    });

    QUnit.test("test grid unavailibility", async (assert) => {
        const { openView } = await start({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {
                        1: ["2017-01-22", "2017-01-24", "2017-01-28"],
                        2: ["2017-01-22", "2017-01-28"],
                        3: ["2017-01-22", "2017-01-28"],
                        4: ["2017-01-22", "2017-01-28"],
                        false: ["2017-01-22", "2017-01-28"],
                    };
                }
                return await timesheetGridSetup.mockTimesheetGridRPC(route, args);
            },
        });

        await openView({
            res_model: "analytic.line",
            views: [[1, "grid"]],
            context: { group_by: [] },
        });

        assert.containsN(target, ".o_grid_section_title", 4);
        assert.containsN(target, ".o_grid_row_title", 6);
        assert.containsN(target, ".o_grid_add_line_first_cell", 2);
        assert.containsN(
            target,
            ".o_grid_unavailable",
            (1 + 4 + 6 + 2 + 1) * 2 + 3,
            "2 whole columns and 3 cells for employee Mario in 2017-01-24 column."
        );
    });
});
