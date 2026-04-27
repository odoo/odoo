/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { setupTestEnv } from "@hr_timesheet/../tests/hr_timesheet_common_tests";

import { patchDate } from "@web/../tests/helpers/utils";

function get_planned_and_worked_hours(resIds) {
    const result = {};
    for (const id of resIds) {
        result[id] = {
            allocated_hours: 8,
            uom: "hours",
            worked_hours: 7,
        };
    }
    return result;
}

function get_timesheet_and_working_hours_for_employees(employeeIds, dateStart, dateEnd) {
    const result = {};
    for (const employeeId of employeeIds) {
        // Employee 11 hasn't done all his hours
        if (employeeId === 1) {
            result[employeeId] = {
                units_to_work: 987,
                uom: "hours",
                worked_hours: 789,
            };
        }

        // Employee 7 has done all his hours
        else if (employeeId === 2) {
            result[employeeId] = {
                units_to_work: 654,
                uom: "hours",
                worked_hours: 654,
            };
        } else if (employeeId === 4) {
            result[employeeId] = {
                units_to_work: 21,
                uom: "days",
                worked_hours: 20,
            };
        } else {
            // The others have done too much hours (overtime)
            result[employeeId] = {
                units_to_work: 6,
                uom: "hours",
                worked_hours: 10,
            };
        }
    }
    return result;
}

function get_daily_working_hours() {
    return {
        1: {
            "2017-01-25": 6,
            "2017-01-27": 6,
        },
        2: {
            "2017-01-24": 8,
            "2017-01-25": 8,
        },
        3: {
            "2017-01-24": 0,
            "2017-01-25": 5.5,
        },
        4: {
            "2017-01-24": 0,
            "2017-01-25": 0,
        },
    };
}

export const timesheetListSetupHelper = {
    setupTimesheetList() {
        setupTestEnv();
    }
}

export class TimesheetGridSetupHelper {
    constructor(withTimer = false) {
        this.withTimer = withTimer;
    }

    async mockTimesheetGridRPC(route, args) {
        if (
            args.method === "get_planned_and_worked_hours" &&
            ["project.project", "project.task"].includes(args.model)
        ) {
            return get_planned_and_worked_hours(...args.args);
        } else if (args.method === "get_timesheet_and_working_hours_for_employees") {
            return get_timesheet_and_working_hours_for_employees(...args.args);
        } else if (args.method === "grid_unavailability") {
            const [dateStart, dateEnd] = args.args;
            const employeeIds = args.kwargs.res_ids || [];
            const unavailabilityDates = Object.fromEntries(
                employeeIds.map((emp) => [emp, [dateStart, dateEnd]])
            );
            unavailabilityDates.false = [dateStart, dateEnd];
            return unavailabilityDates;
        } else if (args.method === "get_last_validated_timesheet_date") {
            return {
                1: false,
                2: "2017-01-30",
                3: "2017-01-29",
            };
        } else if (args.model !== "analytic.line" && args.method === "web_read_group") {
            return {
                groups: [],
                length: 0,
            };
        } else if (args.method === "get_daily_working_hours") {
            return get_daily_working_hours();
        } else if (args.method === "get_timesheet_ranking_data") {
            return {
                "leaderboard": [],
                "employee_id": false,
                "total_time_target": false,
            };
        }
    }

    async mockTimesheetTimerGridRPC(route, args) {
        if (args.method === "get_running_timer") {
            return {
                step_timer: 30,
            };
        } else if (args.method === "action_start_new_timesheet_timer") {
            return false;
        }
        return this.mockTimesheetGridRPC(...arguments);
    }

    async setupTimesheetGrid() {
        const pyEnv = await startServer();
        const [employeeId11, employeeId7, employeeId23, employeeId12] = pyEnv[
            "hr.employee.public"
        ].create([
            {
                name: "Mario",
            },
            {
                name: "Luigi",
            },
            {
                name: "Yoshi",
            },
            {
                name: "Toad",
            },
        ]);

        const [projectId31, projectId142] = pyEnv["project.project"].create([
            { display_name: "P1", allow_timesheets: true },
            { display_name: "Webocalypse Now", allow_timesheets: true },
        ]);

        const [taskId1, taskId12, taskId54] = pyEnv["project.task"].create([
            { display_name: "BS task", project_id: projectId31 },
            { display_name: "Another BS task", project_id: projectId142 },
            { display_name: "yet another task", project_id: projectId142 },
        ]);

        const additionalAnalyticLineFields = {};
        if (this.withTimer) {
            additionalAnalyticLineFields.timer_start = {
                string: "Timer Start",
                type: "datetime",
            };
            additionalAnalyticLineFields.company_id = {
                type: "many2one",
                relation: "res.company",
            };
        }

        pyEnv.mockServer.models["analytic.line"] = {
            fields: {
                id: { string: "ID", type: "integer" },
                name: { string: "Description", type: "char" },
                display_name: { string: "Description", type: "char" },
                project_id: {
                    string: "Project",
                    type: "many2one",
                    relation: "project.project",
                },
                task_id: { string: "Task", type: "many2one", relation: "project.task" },
                employee_id: {
                    string: "Employee",
                    type: "many2one",
                    relation: "hr.employee.public",
                },
                date: { string: "Date", type: "date" },
                unit_amount: { string: "Unit Amount", type: "float", aggregator: "sum" },
                selection_field: {
                    string: "Selection Field",
                    type: "selection",
                    selection: [
                        ["abc", "ABC"],
                        ["def", "DEF"],
                        ["ghi", "GHI"],
                    ],
                },
                display_timer: {string: "Display Timer", type: "boolean"},
                ...additionalAnalyticLineFields,
            },
            records: [
                {
                    id: 1,
                    project_id: projectId31,
                    employee_id: employeeId7,
                    date: "2017-01-24",
                    unit_amount: 2.5,
                    display_timer: true,
                },
                {
                    id: 2,
                    project_id: projectId31,
                    task_id: taskId1,
                    employee_id: employeeId11,
                    date: "2017-01-25",
                    unit_amount: 25,
                },
                {
                    id: 3,
                    project_id: projectId31,
                    task_id: taskId1,
                    employee_id: employeeId23,
                    date: "2017-01-25",
                    unit_amount: 5.5,
                },
                {
                    id: 4,
                    project_id: projectId142,
                    task_id: taskId54,
                    employee_id: employeeId11,
                    date: "2017-01-27",
                    unit_amount: 10,
                },
                {
                    id: 5,
                    project_id: projectId142,
                    task_id: taskId12,
                    employee_id: employeeId7,
                    date: "2017-01-27",
                    unit_amount: -3.5,
                },
                {
                    id: 6,
                    project_id: projectId142,
                    task_id: taskId1,
                    employee_id: employeeId12,
                    date: "2017-01-26",
                    unit_amount: 4,
                },
            ],
        };

        patchDate(2017, 0, 25, 0, 0, 0);

        const serverData = {
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
                        <list>
                            <field name="date" />
                            <field name="project_id" />
                            <field name="task_id" />
                            <field name="selection_field" />
                            <field name="unit_amount" />
                        </list>`,
                "analytic.line,false,grid": `
                        <grid js_class="timesheet_grid" barchart_total="1" create_inline="1">
                            <field name="employee_id" type="row" widget="timesheet_many2one_avatar_employee"/>
                            <field name="project_id" type="row" widget="timesheet_many2one"/>
                            <field name="task_id" type="row" widget="timesheet_many2one"/>
                            <field name="date" type="col">
                                <range name="week" string="Week" span="week" step="day"/>
                                <range name="month" string="Month" span="month" step="day"/>
                                <range name="year" string="Year" span="year" step="month"/>
                            </field>
                            <field name="unit_amount" type="measure" widget="float_time"/>
                            <button string="Action" type="action" name="action_name" />
                        </grid>`,
                "analytic.line,1,grid": `<grid js_class="timesheet_grid" barchart_total="1" create_inline="1">
                        <field name="employee_id" type="row" section="1" widget="timesheet_many2one_avatar_employee"/>
                        <field name="project_id" type="row" widget="timesheet_many2one"/>
                        <field name="task_id" type="row" widget="timesheet_many2one"/>
                        <field name="date" type="col">
                            <range name="week" string="Week" span="week" step="day"/>
                            <range name="month" string="Month" span="month" step="day"/>
                            <range name="year" string="Year" span="year" step="month"/>
                        </field>
                        <field name="unit_amount" type="measure" widget="float_time"/>
                    </grid>`,
                "analytic.line,false,search": `
                        <search>
                            <field name="project_id"/>
                            <filter name="nothing" domain="[(0, '=', 1)]" invisible="1"/>
                            <filter string="Project" name="groupby_project" domain="[]" context="{'group_by': 'project_id'}"/>
                            <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                            <filter string="Selection" name="groupby_selection" domain="[]" context="{'group_by': 'selection_field'}"/>
                        </search>
                    `,
            },
        };
        return { pyEnv, serverData };
    }
}
