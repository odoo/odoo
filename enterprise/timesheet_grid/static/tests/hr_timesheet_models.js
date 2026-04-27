import { serializeDateTime } from "@web/core/l10n/dates";
import { fields, models, onRpc } from "@web/../tests/web_test_helpers";

import { projectModels } from "@project/../tests/project_models";
import { defineTimesheetModels as defineHRTimesheetModels, hrTimesheetModels } from "@hr_timesheet/../tests/hr_timesheet_models";

const { DateTime } = luxon;

export class ProjectProject extends projectModels.ProjectProject {
    allow_timesheets = fields.Boolean();

    _records = [
        { id: 1, name: "P1", allow_timesheets: true },
        { id: 2, name: "Webocalypse Now", allow_timesheets: true },
    ];
}

export class ProjectTask extends projectModels.ProjectTask {
    allow_timesheets = fields.Boolean();

    _records = [
        { id: 1, name: "BS task", project_id: 1 },
        { id: 2, name: "Another BS task", project_id: 2 },
        { id: 3, name: "yet another task", project_id: 2 },
    ];
}

export class HREmployeePublic extends models.Model {
    _name = "hr.employee.public";

    name = fields.Char();

    _records = [
        { id: 1, name: "Mario" },
        { id: 2, name: "Luigi" },
        { id: 3, name: "Yoshi" },
        { id: 4, name: "Toad" },
    ];
}

export class TimerTimer extends models.Model {
    _name = "timer.timer";

    timer_start = fields.Datetime();
    timer_pause = fields.Datetime();
    is_timer_running = fields.Boolean();
    res_model = fields.Char();
    res_id = fields.Integer();
    user_id = fields.Many2one({ relation: "res.users" });

    action_timer_start(resId) {
        if (!this.read(resId, ["timer_start"])[0].timer_start) {
            this.write(resId, {
                timer_start: this.get_server_time(),
            });
        }
    }

    get_server_time() {
        return serializeDateTime(DateTime.now());
    }
}

export class HRTimesheet extends hrTimesheetModels.HRTimesheet {
    timer_start = fields.Datetime();
    timer_pause = fields.Datetime();
    company_id = fields.Many2one({ relation: "res.company" });
    employee_id = fields.Many2one({ relation: "hr.employee.public" });
    date = fields.Date({ default: "2017-01-31" });
    display_timer = fields.Boolean();
    selection_field = fields.Selection({
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });

    action_start_new_timesheet_timer() {
        const timesheetId = this.create({ project_id: 2 });

        // Creating a timer to run usually done "timer.mixin"
        const timer = this.env["timer.timer"].create({
            timer_start: false,
            timer_pause: false,
            is_timer_running: false,
            res_model: this._name,
            res_id: timesheetId,
            user_id: this.env.user.id,
        });
        this.env["timer.timer"].action_timer_start(timer);

        return { id: timer };
    }

    grid_unavailability(dateStart, dateEnd) {
        const { res_ids: employeeIds } = arguments[2];
        const unavailabilityDates = Object.fromEntries(
            employeeIds.map((employee) => [ employee, [ dateStart, dateEnd ] ])
        );
        unavailabilityDates.false = [ dateStart, dateEnd ];
        return unavailabilityDates;
    }

    action_add_time_to_timer() {
        return false;
    }

    action_timer_start() {
        this.action_start_new_timesheet_timer();
        return false;
    }

    action_timer_unlink() {
        return false;
    }

    action_timer_stop() {
        return false;
    }

    get_running_timer() {
        return { step_timer: 30 };
    }

    _records = [
        {
            name: 'youpi',
            id: 1,
            project_id: 1,
            employee_id: 2,
            date: "2017-01-24",
            unit_amount: 2.5,
            display_timer: true,
        },
        {
            name: 'bop',
            id: 2,
            project_id: 1,
            task_id: 1,
            employee_id: 1,
            date: "2017-01-25",
            unit_amount: 25,
        },
        {
            name: 'Sabaton',
            id: 3,
            project_id: 1,
            task_id: 1,
            employee_id: 3,
            date: "2017-01-25",
            unit_amount: 5.5,
        },
        {
            name: 'chaos',
            id: 4,
            project_id: 2,
            task_id: 3,
            employee_id: 1,
            date: "2017-01-27",
            unit_amount: 10,
        },
        {
            name: 'sakamoto',
            id: 5,
            project_id: 2,
            task_id: 2,
            employee_id: 2,
            date: "2017-01-27",
            unit_amount: -3.5,
        },
        {
            name: 'frieren',
            id: 6,
            project_id: 2,
            task_id: 1,
            employee_id: 4,
            date: "2017-01-26",
            unit_amount: 4,
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
            </form>
        `,
        list: `
            <list js_class="timesheet_timer_list">
                <field name="name" />
                <field name="date" />
                <field name="project_id" />
                <field name="task_id" />
                <field name="selection_field" />
                <field name="unit_amount" />
            </list>
        `,
        kanban: `
            <kanban js_class="timesheet_timer_kanban">
                <templates>
                    <field name="name"/>
                    <t t-name="card">
                        <div>
                            <field name="employee_id"/>
                            <field name="project_id"/>
                            <field name="task_id"/>
                            <field name="date"/>
                            <field name="display_timer"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        grid: `
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
            </grid>
        `,
        "grid,1": `
            <grid js_class="timesheet_grid" barchart_total="1" create_inline="1">
                <field name="employee_id" type="row" section="1" widget="timesheet_many2one_avatar_employee"/>
                <field name="project_id" type="row" widget="timesheet_many2one"/>
                <field name="task_id" type="row" widget="timesheet_many2one"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                    <range name="year" string="Year" span="year" step="month"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>
        `,
        search: `
            <search>
                <field name="project_id"/>
                <filter string="Nothing" name="nothing" domain="[(0, '=', 1)]"/>
                <filter string="Project" name="groupby_project" domain="[]" context="{'group_by': 'project_id'}"/>
                <filter string="Task" name="groupby_task" domain="[]" context="{'group_by': 'task_id'}"/>
                <filter string="Selection" name="groupby_selection" domain="[]" context="{'group_by': 'selection_field'}"/>
            </search>
        `,
    };
}

projectModels.ProjectProject = ProjectProject;
projectModels.ProjectTask = ProjectTask;
hrTimesheetModels.HRTimesheet = HRTimesheet;
hrTimesheetModels.HREmployeePublic = HREmployeePublic;
hrTimesheetModels.TimerTimer = TimerTimer;

export function defineTimesheetModels() {
    onRpc(({ method, model, args }) => {
        if (
            method === "get_planned_and_worked_hours" &&
            [ "project.project", "project.task" ].includes(model)
        ) {
            const result = {};
            for (const id of args) {
                result[id] = {
                    allocated_hours: 8,
                    uom: "hours",
                    worked_hours: 7,
                };
            }
            return result;
        } else if (method === "get_timesheet_ranking_data") {
            return {
                "leaderboard": [],
                "employee_id": false,
                "billing_rate_target": false,
                "total_time_target": false,
                "show_leaderboard": true,
            };
        } else if (method === "get_daily_working_hours") {
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
        } else if (method === "get_timesheet_and_working_hours_for_employees") {
            const [ employeeIds ] = args;
            const result = {};
            for (const employeeId of employeeIds) {
                if (employeeId === 1) {
                    // Employee 11 hasn't done all his hours
                    result[employeeId] = {
                        units_to_work: 987,
                        uom: "hours",
                        worked_hours: 789,
                    };
                } else if (employeeId === 2) {
                    // Employee 7 has done all his hours
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
        } else if (method === "get_last_validated_timesheet_date")
            return {
                1: false,
                2: "2017-01-30",
                3: "2017-01-29",
            };
    });
    defineHRTimesheetModels();
}
