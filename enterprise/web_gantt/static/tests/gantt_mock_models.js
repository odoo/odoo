import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export const TASKS_STAGE_SELECTION = [
    ["todo", "To Do"],
    ["in_progress", "In Progress"],
    ["done", "Done"],
    ["cancel", "Cancelled"],
];

export class Project extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Project 1" },
        { id: 2, name: "Project 2" },
    ];
}

export class ResUsers extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }

    _records = [
        { id: 1, name: "User 1" },
        { id: 2, name: "User 2" },
    ];
}

export class Stage extends models.Model {
    name = fields.Char();
    sequence = fields.Integer();

    _records = [
        {
            id: 1,
            name: "in_progress",
            sequence: 2,
        },
        {
            id: 2,
            name: "todo",
            sequence: 1,
        },
        {
            id: 3,
            name: "cancel",
            sequence: 4,
        },
        {
            id: 4,
            name: "done",
            sequence: 3,
        },
    ];
}

export class Tasks extends models.Model {
    name = fields.Char();
    start = fields.Datetime({ string: "Start Date" });
    stop = fields.Datetime({ string: "Stop Date" });
    allocated_hours = fields.Float({ string: "Allocated Hours" });
    stage = fields.Selection({
        selection: TASKS_STAGE_SELECTION,
    });
    color = fields.Integer();
    progress = fields.Integer();
    exclude = fields.Boolean({ string: "Excluded from Consolidation" });
    project_id = fields.Many2one({ relation: "project" });
    stage_id = fields.Many2one({ relation: "stage" });
    user_id = fields.Many2one({ string: "Assign To", relation: "res.users" });

    _records = [
        {
            id: 1,
            name: "Task 1",
            start: "2018-11-30 18:30:00",
            stop: "2018-12-31 18:29:59",
            stage: "todo",
            stage_id: 1,
            project_id: 1,
            user_id: 1,
            color: 0,
            progress: 0,
        },
        {
            id: 2,
            name: "Task 2",
            start: "2018-12-17 11:30:00",
            stop: "2018-12-22 06:29:59",
            stage: "done",
            stage_id: 4,
            project_id: 1,
            user_id: 2,
            color: 2,
            progress: 30,
        },
        {
            id: 3,
            name: "Task 3",
            start: "2018-12-27 06:30:00",
            stop: "2019-01-03 06:29:59",
            stage: "cancel",
            stage_id: 3,
            project_id: 1,
            user_id: 2,
            color: 10,
            progress: 60,
        },
        {
            id: 4,
            name: "Task 4",
            start: "2018-12-20 02:30:00",
            stop: "2018-12-20 06:29:59",
            stage: "in_progress",
            stage_id: 3,
            project_id: 1,
            user_id: 1,
            color: 1,
            exclude: false,
        },
        {
            id: 5,
            name: "Task 5",
            start: "2018-11-08 01:53:10",
            stop: "2018-12-04 01:34:34",
            stage: "done",
            stage_id: 2,
            project_id: 2,
            user_id: 1,
            color: 2,
            progress: 100,
            exclude: true,
        },
        {
            id: 6,
            name: "Task 6",
            start: "2018-11-19 23:00:00",
            stop: "2018-11-20 04:21:01",
            stage: "in_progress",
            stage_id: 4,
            project_id: 2,
            user_id: 1,
            color: 1,
        },
        {
            id: 7,
            name: "Task 7",
            start: "2018-12-20 12:30:12",
            stop: "2018-12-20 18:29:59",
            stage: "cancel",
            stage_id: 1,
            project_id: 2,
            user_id: 2,
            color: 10,
            progress: 80,
        },
        {
            id: 8,
            name: "Task 8",
            start: "2020-03-28 06:30:12",
            stop: "2020-03-28 18:29:59",
            stage: "in_progress",
            stage_id: 1,
            project_id: 2,
            user_id: 2,
            color: 10,
            progress: 80,
        },
    ];
}

export class WorkOrders extends models.Model {
    _name = "workorders";
    name = fields.Char({ string: "name", readonly: false });
    color = fields.Integer({ string: "color", readonly: false });
    cost = fields.Integer({ string: "cost", readonly: true });
    employee = fields.Char({ string: "employee", readonly: false });
    size = fields.Integer({ tring: "size", readonly: false });
    start = fields.Datetime({ string: "Start Date" });
    stop = fields.Datetime({ string: "Stop Date" });

    _records = [
        {
            name: "Work Order 1",
            color: 1,
            cost: 86,
            employee: "Jordan",
            size: 198,
            start: "2018-12-16 05:00:00",
            stop: "2018-12-16 07:00:00",
        },
        {
            name: "Work Order 2",
            color: 2,
            cost: 420,
            employee: "Jordan",
            size: 183,
            start: "2018-12-17 11:30:00",
            stop: "2018-12-17 13:00:00",
        },
        {
            name: "Work Order 3",
            color: 1,
            cost: 86,
            employee: "Michael",
            size: 198,
            start: "2018-12-19 05:00:00",
            stop: "2018-12-19 07:00:00",
        },
    ];
}

export function defineGanttModels() {
    defineModels([Stage, Project, ResUsers, Tasks, WorkOrders]);
}
