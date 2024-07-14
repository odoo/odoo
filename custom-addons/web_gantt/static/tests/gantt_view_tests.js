/** @odoo-module */

import { markup, onPatched, useEffect, useRef } from "@odoo/owl";
import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    nextTick,
    patchDate,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import {
    switchView,
    toggleSearchBarMenu,
    toggleMenuItem,
    validateSearch,
} from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { GanttController } from "@web_gantt/gantt_controller";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import {
    CLASSES,
    dragPill,
    editPill,
    getActiveScale,
    getCell,
    clickCell,
    getCellColorProperties,
    getGridContent,
    getPill,
    getPillWrapper,
    getText,
    getTexts,
    hoverGridCell,
    resizePill,
    SELECTORS,
    setScale,
} from "./helpers";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { localization } from "@web/core/l10n/localization";

function randomName(length) {
    const CHARS = "abcdefghijklmnopqrstuvwxyzàùéèâîûêôäïüëö";
    return [...Array(length)]
        .map(() => {
            const char = CHARS[Math.floor(Math.random() * CHARS.length)];
            return Math.random() < 0.5 ? char : char.toUpperCase();
        })
        .join("");
}

// Hard-coded daylight saving dates from 2019
const DST_DATES = {
    winterToSummer: {
        before: "2019-03-30",
        after: "2019-03-31",
    },
    summerToWinter: {
        before: "2019-10-26",
        after: "2019-10-27",
    },
};

let serverData;
/** @type {HTMLElement} */
let target;
QUnit.module("Views > GanttView", {
    beforeEach() {
        patchDate(2018, 11, 20, 8, 0, 0);

        setupViewRegistries();
        patchWithCleanup(localization, { timeFormat: "hh:mm:ss" });

        target = getFixture();
        serverData = {
            models: {
                tasks: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        start: { string: "Start Date", type: "datetime" },
                        stop: { string: "Stop Date", type: "datetime" },
                        allocated_hours: { string: "Allocated Hours", type: "float" },
                        stage: {
                            string: "Stage",
                            type: "selection",
                            selection: [
                                ["todo", "To Do"],
                                ["in_progress", "In Progress"],
                                ["done", "Done"],
                                ["cancel", "Cancelled"],
                            ],
                        },
                        project_id: { string: "Project", type: "many2one", relation: "projects" },
                        user_id: { string: "Assign To", type: "many2one", relation: "users" },
                        color: { string: "Color", type: "integer" },
                        progress: { string: "Progress", type: "integer" },
                        exclude: { string: "Excluded from Consolidation", type: "boolean" },
                        stage_id: { string: "Stage", type: "many2one", relation: "stage" },
                    },
                    records: [
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
                            progress: false,
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
                            progress: 0,
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
                    ],
                },
                projects: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Project 1" },
                        { id: 2, name: "Project 2" },
                    ],
                },
                users: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "User 1" },
                        { id: 2, name: "User 2" },
                    ],
                },
                stage: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        sequence: { string: "Sequence", type: "integer" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "in_progress",
                            sequence: 2,
                        },
                        {
                            id: 3,
                            name: "cancel",
                            sequence: 4,
                        },
                        {
                            id: 2,
                            name: "todo",
                            sequence: 1,
                        },
                        {
                            id: 4,
                            name: "done",
                            sequence: 3,
                        },
                    ],
                },
            },
            views: {
                "foo,false,gantt": `<gantt/>`,
                "foo,false,search": `<search/>`,
            },
        };
    },
});

// BASIC TESTS

QUnit.test("empty ungrouped gantt rendering", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" />`,
        domain: [["id", "=", 0]],
    });
    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    assert.strictEqual(viewTitle, null);
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [{}]);
    assert.containsNone(target, SELECTORS.noContentHelper);
});

QUnit.test("ungrouped gantt rendering", async (assert) => {
    patchWithCleanup(browser, { setTimeout: (fn) => fn() });

    const task2 = serverData.models.tasks.records[1];
    const startDateLocalString = deserializeDateTime(task2.start).toFormat("f");
    const stopDateLocalString = deserializeDateTime(task2.stop).toFormat("f");

    serverData.views = {
        "tasks,false,gantt": '<gantt date_start="start" date_stop="stop" />',
        "tasks,false,search": "<search/>",
    };

    const webClient = await createWebClient({
        serverData,
        mockRPC(_, { method, model }) {
            if (method === "get_gantt_data") {
                assert.step(model);
            }
        },
    });

    await doAction(webClient, {
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [[false, "gantt"]],
    });
    assert.verifySteps(["tasks"]);

    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    assert.strictEqual(viewTitle, null);
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(columnHeaders.length, 31);
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);
    assert.deepEqual(rows, [
        {
            pills: [
                { title: "Task 5", level: 0, colSpan: "01 -> 04 (1/2)" },
                { title: "Task 1", level: 1, colSpan: "01 -> 31" },
                { title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "Task 4", level: 2, colSpan: "20 -> 20 (1/2)" },
                { title: "Task 7", level: 2, colSpan: "20 (1/2) -> 20" },
                { title: "Task 3", level: 0, colSpan: "27 -> 31" },
            ],
        },
    ]);

    // test popover and local timezone
    assert.containsNone(target, ".o_popover");
    const task2Pill = target.querySelectorAll(SELECTORS.pill)[2];
    assert.strictEqual(getText(task2Pill), "Task 2");
    await click(task2Pill);
    assert.containsOnce(target, ".o_popover");

    assert.deepEqual(getTexts(".o_popover .popover-body span"), [
        "Task 2",
        startDateLocalString,
        stopDateLocalString,
    ]);

    await click(target, ".o_popover .popover-header i.fa.fa-close");
    assert.containsNone(target, ".o_popover");
});

QUnit.test("ordered gantt view", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" progress="progress"/>`,
        groupBy: ["stage_id"],
    });
    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    assert.strictEqual(viewTitle, "Gantt View");
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(columnHeaders.length, 31);
    assert.containsNone(target, SELECTORS.noContentHelper);
    assert.deepEqual(rows, [
        {
            title: "todo",
            pills: [{ level: 0, colSpan: "01 -> 04 (1/2)", title: "Task 5" }],
        },
        {
            title: "in_progress",
            pills: [
                { level: 0, colSpan: "01 -> 31", title: "Task 1" },
                { level: 1, colSpan: "20 (1/2) -> 20", title: "Task 7" },
            ],
        },
        {
            title: "done",
            pills: [{ level: 0, colSpan: "17 (1/2) -> 22 (1/2)", title: "Task 2" }],
        },
        {
            title: "cancel",
            pills: [
                { level: 0, colSpan: "20 -> 20 (1/2)", title: "Task 4" },
                { level: 0, colSpan: "27 -> 31", title: "Task 3" },
            ],
        },
    ]);
});

QUnit.test("empty single-level grouped gantt rendering", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        groupBy: ["project_id"],
        domain: Domain.FALSE.toList(),
    });
    const { viewTitle, range, columnHeaders, rows } = getGridContent();
    assert.strictEqual(viewTitle, "Gantt View");
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [{ title: "" }]);
    assert.containsNone(target, SELECTORS.noContentHelper);
});

QUnit.test("single-level grouped gantt rendering", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop"/>`,
        groupBy: ["project_id"],
    });
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(viewTitle, "Tasks");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [
        {
            title: "Project 1",
            pills: [
                {
                    title: "Task 1",
                    colSpan: "01 -> 31",
                    level: 0,
                },
                {
                    title: "Task 2",
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 1,
                },
                {
                    title: "Task 4",
                    colSpan: "20 -> 20 (1/2)",
                    level: 2,
                },
                {
                    title: "Task 3",
                    colSpan: "27 -> 31",
                    level: 1,
                },
            ],
        },
        {
            title: "Project 2",
            pills: [
                {
                    title: "Task 5",
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                },
                {
                    title: "Task 7",
                    colSpan: "20 (1/2) -> 20",
                    level: 0,
                },
            ],
        },
    ]);
});

QUnit.test("single-level grouped gantt rendering with group_expand", async (assert) => {
    const groups = [
        { project_id: [20, "Unused Project 1"], __record_ids: [] },
        { project_id: [50, "Unused Project 2"], __record_ids: [] },
        { project_id: [2, "Project 2"], __record_ids: [5, 7] },
        { project_id: [30, "Unused Project 3"], __record_ids: [] },
        { project_id: [1, "Project 1"], __record_ids: [1, 2, 3, 4] },
    ];

    patchWithCleanup(MockServer.prototype, {
        mockWebReadGroup() {
            return { groups, length: groups.length };
        },
    });

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop"/>`,
        groupBy: ["project_id"],
    });
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(viewTitle, "Tasks");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [
        { title: "Unused Project 1" },
        { title: "Unused Project 2" },
        {
            title: "Project 2",
            pills: [
                {
                    title: "Task 5",
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                },
                {
                    title: "Task 7",
                    colSpan: "20 (1/2) -> 20",
                    level: 0,
                },
            ],
        },
        { title: "Unused Project 3" },
        {
            title: "Project 1",
            pills: [
                {
                    title: "Task 1",
                    colSpan: "01 -> 31",
                    level: 0,
                },
                {
                    title: "Task 2",
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 1,
                },
                {
                    title: "Task 4",
                    colSpan: "20 -> 20 (1/2)",
                    level: 2,
                },
                {
                    title: "Task 3",
                    colSpan: "27 -> 31",
                    level: 1,
                },
            ],
        },
    ]);
});

QUnit.test("multi-level grouped gantt rendering", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop"/>`,
        groupBy: ["user_id", "project_id", "stage"],
    });
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsN(target, SELECTORS.expandCollapseButtons, 2);

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(viewTitle, "Tasks");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [
        {
            title: "User 1",
            isGroup: true,
            pills: [
                { title: "2", colSpan: "01 -> 04 (1/2)" },
                { title: "1", colSpan: "04 (1/2) -> 19" },
                { title: "2", colSpan: "20 -> 20 (1/2)" },
                { title: "1", colSpan: "20 (1/2) -> 31" },
            ],
        },
        {
            title: "Project 1",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "01 -> 19" },
                { title: "2", colSpan: "20 -> 20 (1/2)" },
                { title: "1", colSpan: "20 (1/2) -> 31" },
            ],
        },
        {
            title: "To Do",
            pills: [{ title: "Task 1", colSpan: "01 -> 31", level: 0 }],
        },
        {
            title: "In Progress",
            pills: [{ title: "Task 4", colSpan: "20 -> 20 (1/2)", level: 0 }],
        },
        {
            title: "Project 2",
            isGroup: true,
            pills: [{ title: "1", colSpan: "01 -> 04 (1/2)" }],
        },
        {
            title: "Done",
            pills: [{ title: "Task 5", colSpan: "01 -> 04 (1/2)", level: 0 }],
        },
        {
            title: "User 2",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "17 (1/2) -> 20 (1/2)" },
                { title: "2", colSpan: "20 (1/2) -> 20" },
                { title: "1", colSpan: "21 -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Done",
            pills: [{ title: "Task 2", colSpan: "17 (1/2) -> 22 (1/2)", level: 0 }],
        },
        {
            title: "Cancelled",
            pills: [{ title: "Task 3", colSpan: "27 -> 31", level: 0 }],
        },
        {
            title: "Project 2",
            isGroup: true,
            pills: [{ title: "1", colSpan: "20 (1/2) -> 20" }],
        },
        {
            title: "Cancelled",
            pills: [{ title: "Task 7", colSpan: "20 (1/2) -> 20", level: 0 }],
        },
    ]);

    assert.ok(
        [...target.querySelectorAll(".o_gantt_group_pill .o_gantt_consolidated_pill")].every(
            (el) => {
                return getComputedStyle(el).backgroundColor === "rgb(113, 75, 103)";
            }
        )
    );
});

QUnit.test("many2many grouped gantt rendering", async (assert) => {
    serverData.models.tasks.fields.user_ids = {
        string: "Assignees",
        type: "many2many",
        relation: "users",
    };
    serverData.models.tasks.records[0].user_ids = [1, 2];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop"/>`,
        groupBy: ["user_ids"],
    });
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(viewTitle, "Tasks");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [
        {
            title: "Undefined Assignees",
            pills: [
                { title: "Task 5", colSpan: "01 -> 04 (1/2)", level: 0 },
                { title: "Task 2", colSpan: "17 (1/2) -> 22 (1/2)", level: 0 },
                { title: "Task 4", colSpan: "20 -> 20 (1/2)", level: 1 },
                { title: "Task 7", colSpan: "20 (1/2) -> 20", level: 1 },
                { title: "Task 3", colSpan: "27 -> 31", level: 0 },
            ],
        },
        {
            title: "User 1",
            pills: [{ title: "Task 1", colSpan: "01 -> 31", level: 0 }],
        },
        {
            title: "User 2",
            pills: [{ title: "Task 1", colSpan: "01 -> 31", level: 0 }],
        },
    ]);
});

QUnit.test("multi-level grouped with many2many field in gantt view", async (assert) => {
    serverData.models.tasks.fields.user_ids = {
        string: "Assignees",
        type: "many2many",
        relation: "users",
    };
    serverData.models.tasks.records[0].user_ids = [1, 2];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt string="Tasks" date_start="start" date_stop="stop"/>`,
        groupBy: ["user_ids", "project_id"],
    });
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsN(target, SELECTORS.expandCollapseButtons, 2);

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    assert.strictEqual(range, "December 2018");
    assert.strictEqual(viewTitle, "Tasks");
    assert.strictEqual(columnHeaders.length, 31);
    assert.deepEqual(rows, [
        {
            title: "Undefined Assignees",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "01 -> 04 (1/2)" },
                { title: "1", colSpan: "17 (1/2) -> 19" },
                { title: "2", colSpan: "20 -> 20 (1/2)" },
                { title: "2", colSpan: "20 (1/2) -> 20" },
                { title: "1", colSpan: "21 -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            pills: [
                { title: "Task 2", colSpan: "17 (1/2) -> 22 (1/2)", level: 0 },
                { title: "Task 4", colSpan: "20 -> 20 (1/2)", level: 1 },
                { title: "Task 3", colSpan: "27 -> 31", level: 0 },
            ],
        },
        {
            title: "Project 2",
            pills: [
                { title: "Task 5", colSpan: "01 -> 04 (1/2)", level: 0 },
                { title: "Task 7", colSpan: "20 (1/2) -> 20", level: 0 },
            ],
        },
        {
            title: "User 1",
            isGroup: true,
            pills: [{ title: "1", colSpan: "01 -> 31" }],
        },
        {
            title: "Project 1",
            pills: [{ title: "Task 1", colSpan: "01 -> 31", level: 0 }],
        },
        {
            title: "User 2",
            isGroup: true,
            pills: [{ title: "1", colSpan: "01 -> 31" }],
        },
        {
            title: "Project 1",
            pills: [{ title: "Task 1", colSpan: "01 -> 31", level: 0 }],
        },
    ]);
});

QUnit.test("full precision gantt rendering", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt date_start="start" default_scale="week" date_stop="stop"
                precision="{'day':'hour:full', 'week':'day:full', 'month':'day:full'}" />
        `,
        groupBy: ["user_id", "project_id"],
    });
    assert.strictEqual(getActiveScale(), "Week");
    assert.containsN(target, SELECTORS.expandCollapseButtons, 2);

    const { range, viewTitle, columnHeaders, rows } = getGridContent();
    assert.strictEqual(range, "16 December 2018 - 22 December 2018");
    assert.strictEqual(viewTitle, "Gantt View");
    assert.strictEqual(columnHeaders.length, 7);
    assert.deepEqual(rows, [
        {
            title: "User 1",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "Sunday, 16 -> Wednesday, 19" },
                { title: "2", colSpan: "Thursday, 20 -> Thursday, 20" },
                { title: "1", colSpan: "Friday, 21 -> Saturday, 22" },
            ],
        },
        {
            title: "Project 1",
            pills: [
                { level: 0, colSpan: "Sunday, 16 -> Saturday, 22", title: "Task 1" },
                { level: 1, colSpan: "Thursday, 20 -> Thursday, 20", title: "Task 4" },
            ],
        },
        {
            title: "User 2",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "Monday, 17 -> Wednesday, 19" },
                { title: "2", colSpan: "Thursday, 20 -> Thursday, 20" },
                { title: "1", colSpan: "Friday, 21 -> Saturday, 22" },
            ],
        },
        {
            title: "Project 1",
            pills: [{ level: 0, colSpan: "Monday, 17 -> Saturday, 22", title: "Task 2" }],
        },
        {
            title: "Project 2",
            pills: [{ level: 0, colSpan: "Thursday, 20 -> Thursday, 20", title: "Task 7" }],
        },
    ]);
});

QUnit.test("gantt rendering, thumbnails", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" thumbnails="{'user_id': 'image'}"/>`,
        groupBy: ["user_id"],
        mockRPC: function (_, args) {
            if (args.method === "get_gantt_data") {
                return {
                    groups: [
                        {
                            user_id: [1, "User 1"],
                            __record_ids: [1],
                        },
                        {
                            user_id: false,
                            __record_ids: [2],
                        },
                    ],
                    length: 2,
                    records: [
                        {
                            display_name: "Task 1",
                            id: 1,
                            start: "2018-11-30 18:30:00",
                            stop: "2018-12-31 18:29:59",
                        },
                        {
                            display_name: "Task 2",
                            id: 2,
                            start: "2018-12-01 18:30:00",
                            stop: "2018-12-02 18:29:59",
                        },
                    ],
                };
            }
        },
    });
    assert.containsOnce(target, SELECTORS.thumbnail);
    assert.ok(
        target
            .querySelector(SELECTORS.thumbnail)
            .dataset.src.endsWith("web/image?model=users&id=1&field=image")
    );
});

QUnit.test("gantt rendering, pills must be chronologically ordered", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt string="Tasks" default_scale="week" date_start="start" date_stop="stop" thumbnails="{'user_id': 'image'}"/>`,
        mockRPC: function (_, args) {
            if (args.method === "get_gantt_data") {
                return {
                    groups: [
                        {
                            user_id: [1, "User 1"],
                            __record_ids: [1],
                        },
                        {
                            user_id: false,
                            __record_ids: [2],
                        },
                    ],
                    length: 2,
                    records: [
                        {
                            display_name: "Task 14:30:00",
                            id: 1,
                            start: "2018-12-17 14:30:00",
                            stop: "2018-12-17 18:29:59",
                        },
                        {
                            display_name: "Task 08:30:00",
                            id: 2,
                            start: "2018-12-17 08:30:00",
                            stop: "2018-12-17 13:29:59",
                        },
                    ],
                };
            }
        },
    });
    const gridContent = getGridContent();
    assert.deepEqual(gridContent.rows, [
        {
            pills: [
                { title: "Task 08:30:00", level: 0, colSpan: "Monday, 17 -> Monday, 17" },
                { title: "Task 14:30:00", level: 1, colSpan: "Monday, 17 (1/2) -> Monday, 17" },
            ],
        },
    ]);
});

QUnit.test("Day scale with 12-hours format", async (assert) => {
    patchWithCleanup(localization, { timeFormat: "hh:mm:ss" });

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day"/>`,
    });

    assert.strictEqual(getActiveScale(), "Day");
    const headers = getGridContent().columnHeaders;
    assert.strictEqual(headers.length, 24);
    assert.deepEqual(headers.slice(0, 4), ["12am", "1am", "2am", "3am"]);
    assert.deepEqual(headers.slice(12, 16), ["12pm", "1pm", "2pm", "3pm"]);
});

QUnit.test("Day scale with 24-hours format", async (assert) => {
    patchWithCleanup(localization, { timeFormat: "HH:mm:ss" });

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" default_scale="day"/>`,
    });

    assert.strictEqual(getActiveScale(), "Day");
    const headers = getGridContent().columnHeaders;
    assert.strictEqual(headers.length, 24);
    assert.deepEqual(headers.slice(0, 4), ["0", "1", "2", "3"]);
    assert.deepEqual(headers.slice(12, 16), ["12", "13", "14", "15"]);
});

QUnit.test("scale switching", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop"/>`,
    });

    // default (month)
    assert.strictEqual(getActiveScale(), "Month");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);
    let gridContent = getGridContent();
    assert.strictEqual(gridContent.range, "December 2018");
    assert.strictEqual(gridContent.columnHeaders.length, 31);
    assert.deepEqual(gridContent.rows, [
        {
            pills: [
                { title: "Task 5", level: 0, colSpan: "01 -> 04 (1/2)" },
                { title: "Task 1", level: 1, colSpan: "01 -> 31" },
                { title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "Task 4", level: 2, colSpan: "20 -> 20 (1/2)" },
                { title: "Task 7", level: 2, colSpan: "20 (1/2) -> 20" },
                { title: "Task 3", level: 0, colSpan: "27 -> 31" },
            ],
        },
    ]);

    // switch to day view
    await setScale("day");

    assert.strictEqual(getActiveScale(), "Day");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);
    gridContent = getGridContent();
    assert.strictEqual(gridContent.range, "Thursday, December 20, 2018");
    assert.strictEqual(gridContent.columnHeaders.length, 24);
    assert.deepEqual(gridContent.rows, [
        {
            pills: [
                { title: "Task 1", level: 0, colSpan: "12am -> 11pm" },
                { title: "Task 2", level: 1, colSpan: "12am -> 11pm" },
                { title: "Task 4", level: 2, colSpan: "3am -> 7am" },
                { title: "Task 7", level: 2, colSpan: "1pm -> 7pm" },
            ],
        },
    ]);

    // switch to week view
    await setScale("week");

    assert.strictEqual(getActiveScale(), "Week");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);
    gridContent = getGridContent();
    assert.strictEqual(gridContent.range, "16 December 2018 - 22 December 2018");
    assert.strictEqual(gridContent.columnHeaders.length, 7);
    assert.deepEqual(gridContent.rows, [
        {
            pills: [
                { title: "Task 1", level: 0, colSpan: "Sunday, 16 -> Saturday, 22" },
                {
                    title: "Task 2",
                    level: 1,
                    colSpan: "Monday, 17 (1/2) -> Saturday, 22 (1/2)",
                },
                { title: "Task 4", level: 2, colSpan: "Thursday, 20 -> Thursday, 20 (1/2)" },
                { title: "Task 7", level: 2, colSpan: "Thursday, 20 (1/2) -> Thursday, 20" },
            ],
        },
    ]);

    // switch to month view
    await setScale("month");

    assert.strictEqual(getActiveScale(), "Month");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);
    gridContent = getGridContent();
    assert.strictEqual(gridContent.range, "December 2018");
    assert.strictEqual(gridContent.columnHeaders.length, 31);
    assert.deepEqual(gridContent.rows, [
        {
            pills: [
                { title: "Task 5", level: 0, colSpan: "01 -> 04 (1/2)" },
                { title: "Task 1", level: 1, colSpan: "01 -> 31" },
                { title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "Task 4", level: 2, colSpan: "20 -> 20 (1/2)" },
                { title: "Task 7", level: 2, colSpan: "20 (1/2) -> 20" },
                { title: "Task 3", level: 0, colSpan: "27 -> 31" },
            ],
        },
    ]);

    // switch to year view
    await setScale("year");

    assert.strictEqual(getActiveScale(), "Year");
    assert.containsNone(target, SELECTORS.expandCollapseButtons);
    gridContent = getGridContent();
    assert.strictEqual(gridContent.range, "2018");
    assert.strictEqual(gridContent.columnHeaders.length, 12);
    assert.deepEqual(gridContent.rows, [
        {
            pills: [
                { title: "Task 5", level: 0, colSpan: "November -> December" },
                { title: "Task 6", level: 1, colSpan: "November -> November" },
                { title: "Task 1", level: 2, colSpan: "November -> December" },
                { title: "Task 2", level: 1, colSpan: "December -> December" },
                { title: "Task 4", level: 3, colSpan: "December -> December" },
                { title: "Task 7", level: 4, colSpan: "December -> December" },
                { title: "Task 3", level: 5, colSpan: "December -> December" },
            ],
        },
    ]);
});

QUnit.test("today is highlighted", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop"/>`,
    });
    assert.containsOnce(target, ".o_gantt_header_cell.o_gantt_today");
    assert.strictEqual(getText(".o_gantt_header_cell.o_gantt_today"), "20");
});

QUnit.test("current month is highlighted'", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="year"/>',
    });

    assert.containsOnce(
        target,
        ".o_gantt_header_cell.o_gantt_today",
        "there should be an highlighted month"
    );
    assert.strictEqual(
        getText(".o_gantt_header_cell.o_gantt_today"),
        "December",
        "the highlighted month should be this month"
    );
});

QUnit.test("current hour is highlighted'", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="day"/>',
    });

    assert.containsOnce(
        target,
        ".o_gantt_header_cell.o_gantt_today",
        "there should be an highlighted hour"
    );
    assert.strictEqual(
        getText(".o_gantt_header_cell.o_gantt_today"),
        "8am",
        "the highlighted hour should correspond to the current time"
    );
});

// GANTT WITH SAMPLE="1"

QUnit.test('empty grouped gantt with sample="1"', async (assert) => {
    serverData.views = {
        "tasks,false,gantt": '<gantt date_start="start" date_stop="stop" sample="1"/>',
        "tasks,false,graph": "<graph/>",
        "tasks,false,search": "<search/>",
    };

    const webClient = await createWebClient({ serverData });

    await doAction(webClient, {
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "graph"],
        ],
        domain: Domain.FALSE.toList(),
        groupBy: ["project_id"],
    });

    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsN(target, SELECTORS.pill, 10);
    assert.containsOnce(target, SELECTORS.noContentHelper);

    const content = target.querySelector(SELECTORS.viewContent).innerHTML;
    await switchView(target, "gantt");
    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.strictEqual(target.querySelector(SELECTORS.viewContent).innerHTML, content);
    assert.containsOnce(target, SELECTORS.noContentHelper);
});

QUnit.test("empty gantt with sample data and default_group_by", async (assert) => {
    serverData.views = {
        "tasks,false,gantt":
            '<gantt date_start="start" date_stop="stop" sample="1" default_group_by="project_id"/>',
        "tasks,false,graph": "<graph/>",
        "tasks,false,search": "<search/>",
    };

    const webClient = await createWebClient({ serverData });

    await doAction(webClient, {
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "graph"],
        ],
        domain: Domain.FALSE.toList(),
    });

    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsN(target, SELECTORS.pill, 10);
    assert.containsOnce(target, SELECTORS.noContentHelper);

    const content = target.querySelector(SELECTORS.viewContent).innerHTML;
    await switchView(target, "gantt");
    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.strictEqual(target.querySelector(SELECTORS.viewContent).innerHTML, content);
    assert.containsOnce(target, SELECTORS.noContentHelper);
});

QUnit.test("empty gantt with sample data and default_group_by (switch view)", async (assert) => {
    serverData.views = {
        "tasks,false,gantt":
            '<gantt date_start="start" date_stop="stop" sample="1" default_group_by="project_id"/>',
        "tasks,false,list": "<list/>",
        "tasks,false,search": "<search/>",
    };

    const webClient = await createWebClient({ serverData });

    await doAction(webClient, {
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "list"],
        ],
        domain: Domain.FALSE.toList(),
    });

    // the gantt view should be in sample mode
    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsN(target, SELECTORS.pill, 10);
    assert.containsOnce(target, SELECTORS.noContentHelper);
    const content = target.querySelector(SELECTORS.viewContent).innerHTML;

    // switch to list view
    await switchView(target, "list");
    assert.containsNone(target, SELECTORS.view);

    // go back to gantt view
    await switchView(target, "gantt");
    assert.containsOnce(target, SELECTORS.view);

    // the gantt view should be still in sample mode
    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsOnce(target, SELECTORS.noContentHelper);
    assert.strictEqual(target.querySelector(SELECTORS.viewContent).innerHTML, content);
});

QUnit.test('empty gantt with sample="1"', async (assert) => {
    serverData.views = {
        "tasks,false,gantt": '<gantt date_start="start" date_stop="stop" sample="1"/>',
        "tasks,false,graph": "<graph/>",
        "tasks,false,search": "<search/>",
    };

    const webClient = await createWebClient({ serverData });

    await doAction(webClient, {
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "graph"],
        ],
        domain: Domain.FALSE.toList(),
    });

    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsN(target, SELECTORS.pill, 10);
    assert.containsOnce(target, SELECTORS.noContentHelper);

    const content = target.querySelector(SELECTORS.viewContent).innerHTML;
    await switchView(target, "gantt");
    assert.hasClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.strictEqual(target.querySelector(SELECTORS.viewContent).innerHTML, content);
    assert.containsOnce(target, SELECTORS.noContentHelper);
});

QUnit.test('non empty gantt with sample="1"', async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" default_scale="year" sample="1"/>`,
        searchViewArch: `
            <search>
                <filter name="filter" string="False Domain" domain="[(0, '=', 1)]"/>
            </search>
        `,
    });

    assert.doesNotHaveClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsN(target, SELECTORS.cell, 12);
    assert.containsN(target, SELECTORS.pill, 7);
    assert.containsNone(target, SELECTORS.noContentHelper);

    await toggleSearchBarMenu(target);
    await toggleMenuItem(target, "False Domain");

    assert.doesNotHaveClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsNone(target, SELECTORS.pill);
    assert.containsNone(target, SELECTORS.noContentHelper);
    assert.containsN(target, SELECTORS.cell, 12);
});

QUnit.test('non empty grouped gantt with sample="1"', async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" default_scale="year" sample="1"/>`,
        groupBy: ["project_id"],
        searchViewArch: `
            <search>
                <filter name="filter" string="False Domain" domain="[(0, '=', 1)]"/>
            </search>
        `,
    });

    assert.doesNotHaveClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsN(target, SELECTORS.cell, 24);
    assert.containsN(target, SELECTORS.pill, 7);

    await toggleSearchBarMenu(target);
    await toggleMenuItem(target, "False Domain");

    assert.doesNotHaveClass(target.querySelector(SELECTORS.viewContent), "o_view_sample_data");
    assert.containsNone(target, SELECTORS.pill);
    assert.containsNone(target, SELECTORS.noContentHelper);
    assert.containsN(target, SELECTORS.cell, 12);
});

QUnit.test("no content helper from action when no data and sample mode", async (assert) => {
    serverData.models.tasks.records = [];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" sample="1"/>`,
        noContentHelp: markup('<p class="hello">click to add a partner</p>'),
    });

    assert.containsOnce(target, SELECTORS.noContentHelper);
    assert.containsOnce(target, `${SELECTORS.noContentHelper} p.hello:contains(add a partner)`);
});

// BEHAVIORAL TESTS

QUnit.test("date navigation with timezone (1h)", async (assert) => {
    patchWithCleanup(browser, { setTimeout: (fn) => fn() });

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        mockRPC(_, { method, kwargs }) {
            if (method === "get_gantt_data") {
                assert.step(kwargs.domain.toString());
            }
        },
    });
    assert.verifySteps(["&,start,<=,2018-12-31 22:59:59,stop,>=,2018-11-30 23:00:00"]);
    assert.strictEqual(getGridContent().range, "December 2018");

    // month navigation
    await click(target, SELECTORS.prevButton);
    assert.verifySteps(["&,start,<=,2018-11-30 22:59:59,stop,>=,2018-10-31 23:00:00"]);
    assert.strictEqual(getGridContent().range, "November 2018");

    await click(target, SELECTORS.nextButton);
    assert.verifySteps(["&,start,<=,2018-12-31 22:59:59,stop,>=,2018-11-30 23:00:00"]);
    assert.strictEqual(getGridContent().range, "December 2018");

    // switch to day view and check day navigation
    await setScale("day");

    assert.verifySteps(["&,start,<=,2018-12-20 22:59:59,stop,>=,2018-12-19 23:00:00"]);
    assert.strictEqual(getGridContent().range, "Thursday, December 20, 2018");

    await click(target, SELECTORS.prevButton);
    assert.verifySteps(["&,start,<=,2018-12-19 22:59:59,stop,>=,2018-12-18 23:00:00"]);
    assert.strictEqual(getGridContent().range, "Wednesday, December 19, 2018");

    await click(target, SELECTORS.nextButton);
    assert.verifySteps(["&,start,<=,2018-12-20 22:59:59,stop,>=,2018-12-19 23:00:00"]);
    assert.strictEqual(getGridContent().range, "Thursday, December 20, 2018");

    // switch to week view and check week navigation
    await setScale("week");

    assert.verifySteps(["&,start,<=,2018-12-22 22:59:59,stop,>=,2018-12-15 23:00:00"]);
    assert.strictEqual(getGridContent().range, "16 December 2018 - 22 December 2018");

    await click(target, SELECTORS.prevButton);
    assert.verifySteps(["&,start,<=,2018-12-15 22:59:59,stop,>=,2018-12-08 23:00:00"]);
    assert.strictEqual(getGridContent().range, "09 December 2018 - 15 December 2018");

    await click(target, SELECTORS.nextButton);
    assert.verifySteps(["&,start,<=,2018-12-22 22:59:59,stop,>=,2018-12-15 23:00:00"]);
    assert.strictEqual(getGridContent().range, "16 December 2018 - 22 December 2018");

    // switch to year view and check year navigation
    await setScale("year");

    assert.verifySteps(["&,start,<=,2018-12-31 22:59:59,stop,>=,2017-12-31 23:00:00"]);
    assert.strictEqual(getGridContent().range, "2018");

    await click(target, SELECTORS.prevButton);
    assert.verifySteps(["&,start,<=,2017-12-31 22:59:59,stop,>=,2016-12-31 23:00:00"]);
    assert.strictEqual(getGridContent().range, "2017");

    await click(target, SELECTORS.nextButton);
    assert.verifySteps(["&,start,<=,2018-12-31 22:59:59,stop,>=,2017-12-31 23:00:00"]);
    assert.strictEqual(getGridContent().range, "2018");
});

QUnit.test(
    "if a on_create is specified, execute the action rather than opening a dialog. And reloads after the action",
    async (assert) => {
        const actionService = {
            start() {
                return {
                    doAction(action, options) {
                        assert.step(`[action] ${action}`);
                        assert.deepEqual(options.additionalContext, {
                            default_start: "2018-11-30 23:00:00",
                            default_stop: "2018-12-31 22:59:59",
                            lang: "en",
                            start: "2018-11-30 23:00:00",
                            stop: "2018-12-31 22:59:59",
                            tz: "taht",
                            uid: 7,
                        });
                        options.onClose();
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: '<gantt date_start="start" date_stop="stop" on_create="this_is_create_action" />',
            mockRPC: function (_, { method }) {
                if (method === "get_gantt_data") {
                    assert.step("get_gantt_data");
                }
            },
        });

        assert.verifySteps(["get_gantt_data"]);
        await click($(SELECTORS.addButton + ":visible").get(0));
        assert.verifySteps(["[action] this_is_create_action", "get_gantt_data"]);
    }
);

QUnit.test("select cells to plan a task", async (assert) => {
    const dialogService = {
        start() {
            return {
                add(_, props) {
                    assert.step(`[dialog] ${props.title}`);
                    assert.deepEqual(props.context, {
                        default_start: "2018-11-30 23:00:00",
                        default_stop: "2018-12-02 22:59:59",
                        lang: "en",
                        start: "2018-11-30 23:00:00",
                        stop: "2018-12-02 22:59:59",
                        tz: "taht",
                        uid: 7,
                    });
                },
            };
        },
    };
    registry.category("services").add("dialog", dialogService, { force: true });
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop"/>',
    });
    await hoverGridCell(1, 1);
    await triggerEvent(getCell(1, 1), null, "pointerdown");
    await hoverGridCell(1, 2);
    await triggerEvent(getCell(1, 2), null, "pointerup");
    assert.verifySteps(["[dialog] Plan"]);
});

QUnit.test("row id is properly escaped to avoid name issues in selection", async (assert) => {
    const dialogService = {
        start() {
            return {
                add() {
                    assert.step(`[dialog]`);
                },
            };
        },
    };
    serverData.models.users.records[0].name = "O'Reilly";
    registry.category("services").add("dialog", dialogService, { force: true });
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_group_by="user_id"/>',
    });
    await hoverGridCell(1, 1);
    await clickCell(1, 1);
    assert.verifySteps(["[dialog]"]);
});

QUnit.test("select cells to plan a task: 1-level grouped", async (assert) => {
    const dialogService = {
        start() {
            return {
                add(_, props) {
                    assert.step(`[dialog] ${props.title}`);
                    assert.deepEqual(props.context, {
                        default_start: "2018-11-30 23:00:00",
                        default_stop: "2018-12-02 22:59:59",
                        default_user_id: 1,
                        lang: "en",
                        start: "2018-11-30 23:00:00",
                        stop: "2018-12-02 22:59:59",
                        tz: "taht",
                        uid: 7,
                        user_id: 1,
                    });
                },
            };
        },
    };
    registry.category("services").add("dialog", dialogService, { force: true });
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop"/>',
        groupBy: ["user_id"],
    });
    await hoverGridCell(1, 1);
    await triggerEvent(getCell(1, 1), null, "pointerdown");
    await hoverGridCell(1, 2);
    await triggerEvent(getCell(1, 2), null, "pointerup");
    assert.verifySteps(["[dialog] Plan"]);
});

QUnit.test("select cells to plan a task: 2-level grouped", async (assert) => {
    const dialogService = {
        start() {
            return {
                add(_, props) {
                    assert.step(`[dialog] ${props.title}`);
                    assert.deepEqual(props.context, {
                        default_project_id: 1,
                        default_start: "2018-11-30 23:00:00",
                        default_stop: "2018-12-02 22:59:59",
                        default_user_id: 1,
                        lang: "en",
                        project_id: 1,
                        start: "2018-11-30 23:00:00",
                        stop: "2018-12-02 22:59:59",
                        tz: "taht",
                        uid: 7,
                        user_id: 1,
                    });
                },
            };
        },
    };
    registry.category("services").add("dialog", dialogService, { force: true });
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop"/>',
        groupBy: ["user_id", "project_id"],
    });
    await hoverGridCell(1, 1);
    await triggerEvent(getCell(1, 1), null, "pointerdown");
    await hoverGridCell(1, 2);
    await triggerEvent(getCell(1, 2), null, "pointerup");
    // nothing happens
    await hoverGridCell(2, 1);
    await triggerEvent(getCell(2, 1), null, "pointerdown");
    await hoverGridCell(2, 2);
    await triggerEvent(getCell(2, 2), null, "pointerup");
    assert.verifySteps(["[dialog] Plan"]);
});

QUnit.test("hovering a cell with special character", async (assert) => {
    assert.expect(1);
    // add special character to data
    serverData.models.users.records[0].name = "User' 1";

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop"/>',
        groupBy: ["user_id", "project_id"],
    });

    // hover on first header "User' 1" with data-row-id equal to [{"user_id":[1,"User' 1"]}]
    // the "'" must be escaped with "\\'" in findSiblings to prevent the selector to crash
    await triggerEvent(target.querySelector(".o_gantt_row_header"), null, "pointerenter");
    assert.hasClass(
        target.querySelector(".o_gantt_row_header"),
        "o_gantt_group_hovered",
        "hover style is applied to the element"
    );
});

QUnit.test("open a dialog to add a new task", async (assert) => {
    serverData.views = {
        "tasks,false,form": `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
            </form>
        `,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
    });
    assert.containsNone(target, ".modal");
    await click($(SELECTORS.addButton + ":visible").get(0));

    // check that the dialog is opened with prefilled fields
    assert.containsOnce(target, ".modal");
    const modal = target.querySelector(".modal");
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=start] input").value,
        "12/01/2018 00:00:00"
    );
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=stop] input").value,
        "12/31/2018 23:59:59"
    );
});

QUnit.test("open a dialog to create/edit a task", async (assert) => {
    serverData.views = {
        "tasks,false,form": `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
                <field name="stage"/>
                <field name="project_id"/>
                <field name="user_id"/>
            </form>
        `,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" plan="false"/>',
        groupBy: ["user_id", "project_id", "stage"],
    });

    // open dialog to create a task
    assert.containsNone(target, ".modal");
    await hoverGridCell(4, 10);
    await clickCell(4, 10);

    // check that the dialog is opened with prefilled fields
    assert.containsOnce(target, ".modal");
    let modal = target.querySelector(".modal");
    assert.strictEqual(getText(".modal-title"), "Create");
    await editInput(target, ".o_field_widget[name=name] input", "Task 8");
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=start] input").value,
        "12/10/2018 00:00:00"
    );
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=stop] input").value,
        "12/10/2018 23:59:59"
    );
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=project_id] input").value,
        "Project 1"
    );
    assert.strictEqual(modal.querySelector(".o_field_widget[name=user_id] input").value, "User 1");
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=stage] select").value,
        '"in_progress"'
    );

    // create the task
    await click(modal, ".o_form_button_save");
    assert.containsNone(target, ".modal");

    // open dialog to view a task
    await editPill("Task 8");
    assert.containsOnce(target, ".modal");
    modal = target.querySelector(".modal");
    assert.strictEqual(getText(".modal-title"), "Open");
    assert.strictEqual(modal.querySelector(".o_field_widget[name=name] input").value, "Task 8");
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=start] input").value,
        "12/10/2018 00:00:00"
    );
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=stop] input").value,
        "12/10/2018 23:59:59"
    );
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=project_id] input").value,
        "Project 1"
    );
    assert.strictEqual(modal.querySelector(".o_field_widget[name=user_id] input").value, "User 1");
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=stage] select").value,
        '"in_progress"'
    );
});

QUnit.test("open a dialog to create a task when grouped by many2many field", async (assert) => {
    patchWithCleanup(browser, { setTimeout: (fn) => fn() });
    serverData.models.tasks.fields.user_ids = {
        string: "Assignees",
        type: "many2many",
        relation: "users",
    };
    serverData.models.tasks.records[0].user_ids = [1, 2];
    serverData.views = {
        "tasks,false,form": `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
                <field name="project_id"/>
                <field name="user_ids" widget="many2many_tags"/>
            </form>
        `,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" plan="false"/>`,
        groupBy: ["user_ids", "project_id"],
    });

    // Check grouped rows
    assert.deepEqual(getGridContent().rows, [
        {
            title: "Undefined Assignees",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "01 -> 04 (1/2)" },
                { title: "1", colSpan: "17 (1/2) -> 19" },
                { title: "2", colSpan: "20 -> 20 (1/2)" },
                { title: "2", colSpan: "20 (1/2) -> 20" },
                { title: "1", colSpan: "21 -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            pills: [
                { level: 0, colSpan: "17 (1/2) -> 22 (1/2)", title: "Task 2" },
                { level: 1, colSpan: "20 -> 20 (1/2)", title: "Task 4" },
                { level: 0, colSpan: "27 -> 31", title: "Task 3" },
            ],
        },
        {
            title: "Project 2",
            pills: [
                { level: 0, colSpan: "01 -> 04 (1/2)", title: "Task 5" },
                { level: 0, colSpan: "20 (1/2) -> 20", title: "Task 7" },
            ],
        },
        {
            title: "User 1",
            isGroup: true,
            pills: [{ title: "1", colSpan: "01 -> 31" }],
        },
        {
            title: "Project 1",
            pills: [{ level: 0, colSpan: "01 -> 31", title: "Task 1" }],
        },
        {
            title: "User 2",
            isGroup: true,
            pills: [{ title: "1", colSpan: "01 -> 31" }],
        },
        {
            title: "Project 1",
            pills: [{ level: 0, colSpan: "01 -> 31", title: "Task 1" }],
        },
    ]);

    // open dialog to create a task with two many2many values
    await hoverGridCell(5, 10);
    await clickCell(5, 10);
    let modal = target.querySelector(".modal");
    await editInput(modal, ".o_field_widget[name=name] input", "NEW TASK 0");
    await editInput(modal, ".o_field_widget[name=user_ids] input", "User 2");
    await click(modal, ".o-autocomplete--dropdown-menu li:first-child a");
    await click(modal, ".o_form_button_save");
    assert.containsNone(target, ".modal");
    const [, , , , fifthRow, , seventhRow] = getGridContent().rows;
    assert.deepEqual(fifthRow, {
        title: "Project 1",
        pills: [
            { level: 0, colSpan: "01 -> 31", title: "Task 1" },
            { level: 1, colSpan: "10 -> 10", title: "NEW TASK 0" },
        ],
    });
    assert.deepEqual(seventhRow, {
        title: "Project 1",
        pills: [
            { level: 0, colSpan: "01 -> 31", title: "Task 1" },
            { level: 1, colSpan: "10 -> 10", title: "NEW TASK 0" },
        ],
    });

    // open dialog to create a task with no many2many values
    await hoverGridCell(3, 24);
    await clickCell(3, 24);
    modal = target.querySelector(".modal");
    await editInput(modal, ".o_field_widget[name=name] input", "NEW TASK 1");
    await click(modal, ".o_form_button_save");
    assert.containsNone(target, ".modal");
    const [, , thirdRow] = getGridContent().rows;
    assert.deepEqual(thirdRow, {
        title: "Project 2",
        pills: [
            { level: 0, colSpan: "01 -> 04 (1/2)", title: "Task 5" },
            { level: 0, colSpan: "20 (1/2) -> 20", title: "Task 7" },
            { level: 0, colSpan: "24 -> 24", title: "NEW TASK 1" },
        ],
    });
});

QUnit.test("open a dialog to create a task, does not have a delete button", async (assert) => {
    serverData.views = {
        "tasks,false,form": `<form><field name="name"/></form>`,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" plan="false"/>',
        groupBy: [],
    });
    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    assert.containsNone(target, ".modal .o_btn_remove");
});

QUnit.test("open a dialog to edit a task, has a delete buttton", async (assert) => {
    serverData.views = {
        "tasks,false,form": `<form><field name="name"/></form>`,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: [],
    });
    await editPill("Task 1");
    assert.containsOnce(target, ".modal .o_form_button_remove");
});

QUnit.test(
    "clicking on delete button in edit dialog triggers a confirmation dialog, clicking discard does not call unlink on the model",
    async (assert) => {
        serverData.views = {
            "tasks,false,form": `<form><field name="name"/></form>`,
        };
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: '<gantt date_start="start" date_stop="stop" />',
            groupBy: [],
            mockRPC(route, { method }) {
                if (method === "unlink") {
                    assert.step(method);
                }
            },
        });
        assert.containsNone(target, ".o_dialog");
        await editPill("Task 1");
        assert.containsOnce(target, ".o_dialog");
        // trigger the delete button
        await click(target, ".o_dialog .o_form_button_remove");
        assert.containsN(target, ".o_dialog", 2);

        const button = target.querySelector(
            ".o_dialog:not(.o_inactive_modal) footer .btn-secondary"
        );
        assert.strictEqual(getText(button), "Cancel");
        await click(button);
        assert.containsOnce(target, ".o_dialog");
        assert.verifySteps([]);
    }
);

QUnit.test(
    "clicking on delete button in edit dialog triggers a confirmation dialog, clicking ok call unlink on the model",
    async (assert) => {
        serverData.views = {
            "tasks,false,form": `<form><field name="name"/></form>`,
        };
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: '<gantt date_start="start" date_stop="stop" />',
            groupBy: [],
            mockRPC(route, { method }) {
                if (method === "unlink") {
                    assert.step(method);
                }
            },
        });
        assert.containsNone(target, ".o_dialog");
        await editPill("Task 1");
        assert.containsOnce(target, ".o_dialog");
        // trigger the delete button
        await click(target, ".o_dialog .o_form_button_remove");
        assert.containsN(target, ".o_dialog", 2);

        const button = target.querySelector(".o_dialog:not(.o_inactive_modal) footer .btn-primary");
        assert.strictEqual(getText(button), "Ok");
        await click(button);
        assert.containsNone(target, ".o_dialog");
        assert.verifySteps(["unlink"]);
        // Check that the pill has disappeared
        try {
            await editPill("Task 1");
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps(['Could not find pill with text "Task 1" (nth: 1)']);
    }
);

QUnit.test("create dialog with timezone", async (assert) => {
    assert.expect(3);
    serverData.views = {
        "tasks,false,form": `<form><field name="start"/><field name="stop"/></form>`,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" plan="false"/>',
        mockRPC(route, { method, args }) {
            if (method === "web_save") {
                assert.deepEqual(args[1], {
                    start: "2018-12-09 23:00:00",
                    stop: "2018-12-10 22:59:59",
                });
            }
        },
    });
    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    const modal = target.querySelector(".modal");
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=start] input").value,
        "12/10/2018 00:00:00"
    );
    assert.strictEqual(
        modal.querySelector(".o_field_widget[name=stop] input").value,
        "12/10/2018 23:59:59"
    );
    await click(modal, ".o_form_button_save");
});

QUnit.test("open a dialog to plan a task", async (assert) => {
    serverData.views = {
        "tasks,false,list": '<tree><field name="name"/></tree>',
        "tasks,false,search": '<search><field name="name"/></search>',
    };
    serverData.models.tasks.records.push(
        { id: 41, name: "Task 41" },
        { id: 42, name: "Task 42", stop: "2018-12-31 18:29:59" },
        { id: 43, name: "Task 43", start: "2018-11-30 18:30:00" }
    );
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        mockRPC(route, { method, args, model }) {
            if (method === "write") {
                assert.step(model);
                assert.deepEqual(args[0], [41, 42], "should write on the selected ids");
                assert.deepEqual(args[1], {
                    start: "2018-12-09 23:00:00",
                    stop: "2018-12-10 22:59:59",
                });
            }
        },
    });

    // click on the plan button
    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    assert.containsOnce(target, ".modal .o_list_view");
    assert.deepEqual(getTexts(".modal .o_list_view .o_data_cell"), [
        "Task 41",
        "Task 42",
        "Task 43",
    ]);

    // Select the first two tasks
    await click(target, ".modal .o_list_view tbody tr:nth-child(1) input");
    await click(target, ".modal .o_list_view tbody tr:nth-child(2) input");
    await click(target, ".modal footer .o_select_button");
    assert.verifySteps(["tasks"]);
});

QUnit.test("open a dialog to plan a task (multi-level)", async (assert) => {
    serverData.views = {
        "tasks,false,list": '<tree><field name="name"/></tree>',
        "tasks,false,search": '<search><field name="name"/></search>',
    };
    serverData.models.tasks.records.push({ id: 41, name: "Task 41" });

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        mockRPC(route, { args, method, model }) {
            if (method === "write") {
                assert.step(model);
                assert.deepEqual(args[0], [41], "should write on the selected id");
                assert.deepEqual(
                    args[1],
                    {
                        project_id: 1,
                        stage: "todo",
                        start: "2018-12-09 23:00:00",
                        stop: "2018-12-10 22:59:59",
                        user_id: 1,
                    },
                    "should write on all the correct fields"
                );
            }
        },
        groupBy: ["user_id", "project_id", "stage"],
    });

    // click on the plan button
    await hoverGridCell(3, 10);
    await clickCell(3, 10);
    assert.containsOnce(target, ".modal .o_list_view");
    assert.deepEqual(getText(".modal .o_list_view .o_data_cell"), "Task 41");

    // Select the first task
    await click(target, ".modal .o_list_view tbody tr:nth-child(1) input");
    await nextTick();
    await click(target, ".modal-footer .o_select_button");
    assert.verifySteps(["tasks"]);
});

QUnit.test("expand/collapse rows", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["user_id", "project_id", "stage"],
    });
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "To Do" },
            { title: "In Progress" },
            { title: "Project 2", isGroup: true },
            { title: "Done" },
            { title: "User 2", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "Done" },
            { title: "Cancelled" },
            { title: "Project 2", isGroup: true },
            { title: "Cancelled" },
        ]
    );

    // collapse all groups
    await click(target, SELECTORS.collapseButton);
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "User 2", isGroup: true },
        ]
    );

    // expand all groups
    await click(target, SELECTORS.expandButton);
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "To Do" },
            { title: "In Progress" },
            { title: "Project 2", isGroup: true },
            { title: "Done" },
            { title: "User 2", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "Done" },
            { title: "Cancelled" },
            { title: "Project 2", isGroup: true },
            { title: "Cancelled" },
        ]
    );

    // collapse the first group
    await click(target, `${SELECTORS.rowHeader}${SELECTORS.group}:nth-child(1)`);
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "User 2", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "Done" },
            { title: "Cancelled" },
            { title: "Project 2", isGroup: true },
            { title: "Cancelled" },
        ]
    );
});

QUnit.test("collapsed rows remain collapsed at reload", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["user_id", "project_id", "stage"],
    });
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "To Do" },
            { title: "In Progress" },
            { title: "Project 2", isGroup: true },
            { title: "Done" },
            { title: "User 2", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "Done" },
            { title: "Cancelled" },
            { title: "Project 2", isGroup: true },
            { title: "Cancelled" },
        ]
    );

    // collapse the first group
    await click(target, `${SELECTORS.rowHeader}${SELECTORS.group}:nth-child(1)`);
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "User 2", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "Done" },
            { title: "Cancelled" },
            { title: "Project 2", isGroup: true },
            { title: "Cancelled" },
        ]
    );

    // reload
    await validateSearch(target);
    assert.deepEqual(
        getGridContent().rows.map((r) => omit(r, "pills")),
        [
            { title: "User 1", isGroup: true },
            { title: "User 2", isGroup: true },
            { title: "Project 1", isGroup: true },
            { title: "Done" },
            { title: "Cancelled" },
            { title: "Project 2", isGroup: true },
            { title: "Cancelled" },
        ]
    );
});

QUnit.test("resize a pill", async (assert) => {
    assert.expect(12);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 1]],
        async mockRPC(_route, { args, method }) {
            if (method === "write") {
                // initial dates -- start: '2018-11-30 18:30:00', stop: '2018-12-31 18:29:59'
                assert.step(JSON.stringify(args));
            }
        },
    });

    assert.containsOnce(target, SELECTORS.pill, "there should be one pill (Task 1)");
    assert.containsOnce(target, SELECTORS.resizable);
    assert.containsNone(target, SELECTORS.resizeHandle);

    await triggerEvent(getPillWrapper("Task 1"), null, "pointerenter");

    // No start resizer because the start date overflows
    assert.containsNone(target, SELECTORS.resizeStartHandle);
    assert.containsOnce(target, SELECTORS.resizeEndHandle);

    // resize to one cell smaller at end (-1 day)
    await resizePill(getPillWrapper("Task 1"), "end", -1);

    // go to previous month (november)
    await click(target, SELECTORS.prevButton);

    assert.containsOnce(target, ".o_gantt_pill", "there should still be one pill (Task 1)");
    assert.containsOnce(target, SELECTORS.resizable);

    await triggerEvent(getPillWrapper("Task 1"), null, "pointerenter");

    // No end resizer because the end date overflows
    assert.containsOnce(target, SELECTORS.resizeStartHandle);
    assert.containsNone(target, SELECTORS.resizeEndHandle);

    // resize to one cell smaller at start (-1 day)
    await resizePill(getPillWrapper("Task 1"), "start", -1);

    assert.verifySteps([
        JSON.stringify([[1], { stop: "2018-12-30 18:29:59" }]),
        JSON.stringify([[1], { start: "2018-11-29 18:30:00" }]),
    ]);
});

QUnit.test("resize pill in year mode", async (assert) => {
    assert.expect(2);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="year" />',
        async mockRPC(_route, { method }) {
            if (method === "write") {
                throw new Error("Should not call write");
            }
        },
    });

    const initialPillWidth = getPillWrapper("Task 5").getBoundingClientRect().width;

    assert.hasClass(getPillWrapper("Task 5"), CLASSES.resizable);

    // Resize way over the limit
    await resizePill(getPillWrapper("Task 5"), "end", 0, { x: 200 });

    assert.strictEqual(
        initialPillWidth,
        getPillWrapper("Task 5").getBoundingClientRect().width,
        "the pill should have the same width as before the resize"
    );
});

QUnit.test("resize a pill (2)", async (assert) => {
    assert.expect(6);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 2]],
        async mockRPC(_route, { args, method }) {
            if (method === "write") {
                assert.step(JSON.stringify(args));
            }
        },
    });

    assert.containsOnce(target, SELECTORS.pill);

    await triggerEvent(getPillWrapper("Task 2"), null, "pointerenter");

    assert.hasClass(getPillWrapper("Task 2"), CLASSES.resizable);
    assert.containsN(target, SELECTORS.resizeHandle, 2);

    // resize to one cell larger
    await resizePill(getPillWrapper("Task 2"), "end", +1);

    assert.containsNone(document.body, ".modal");
    assert.verifySteps([JSON.stringify([[2], { stop: "2018-12-23 06:29:59" }])]);
});

QUnit.test("resize a pill: quickly enter the neighbour pill when resize start", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "in", [4, 7]]],
    });
    assert.containsN(target, SELECTORS.pill, 2);

    await triggerEvent(getPillWrapper("Task 4"), null, "pointerenter");
    assert.containsN(getPillWrapper("Task 4"), SELECTORS.resizeHandle, 2);

    // Here we simulate a resize start on Task 4 and quickly enter Task 7
    // The resize handle should not be added to Task 7
    await triggerEvent(getPillWrapper("Task 4"), SELECTORS.resizeEndHandle, "pointerdown");
    await triggerEvent(getPillWrapper("Task 7"), null, "pointerenter");
    assert.containsN(getPillWrapper("Task 4"), SELECTORS.resizeHandle, 2);
    assert.containsNone(getPillWrapper("Task 7"), SELECTORS.resizeHandle);
});

QUnit.test("create a task maintains the domain", async (assert) => {
    serverData.views["tasks,false,form"] = '<form><field name="name"/></form>';
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" plan="false"></gantt>',
        domain: [["user_id", "=", 2]], // I am an important line
    });
    assert.containsN(target, SELECTORS.pill, 3);
    await hoverGridCell(1, 1);
    await clickCell(1, 1);

    await editInput(target, ".modal [name=name] input", "new task");
    await click(target, ".modal .o_form_button_save");
    assert.containsN(target, SELECTORS.pill, 3);
});

QUnit.test("pill is updated after failed resized", async (assert) => {
    assert.expect(5);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 7]],
        async mockRPC(_route, { method }) {
            switch (method) {
                case "get_gantt_data": {
                    assert.step(method);
                    break;
                }
                case "write": {
                    assert.step(method);
                    throw "WRITING FORBIDDEN";
                }
            }
        },
    });

    const initialPillWidth = getPillWrapper("Task 7").getBoundingClientRect().width;

    // resize to one cell larger (1 day)
    await resizePill(getPillWrapper("Task 7"), "end", +1);

    assert.strictEqual(initialPillWidth, getPillWrapper("Task 7").getBoundingClientRect().width);

    assert.verifySteps(["get_gantt_data", "write", "get_gantt_data"]);
});

QUnit.test("move a pill in the same row", async (assert) => {
    assert.expect(5);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 7]],
        mockRPC(_route, { args, method }) {
            if (method === "write") {
                assert.deepEqual(args[0], [7], "should write on the correct record");
                assert.deepEqual(
                    args[1],
                    {
                        start: "2018-12-21 12:30:12",
                        stop: "2018-12-21 18:29:59",
                    },
                    "both start and stop date should be correctly set (+1 day)"
                );
            }
        },
    });

    assert.hasClass(getPillWrapper("Task 7"), CLASSES.draggable);
    assert.deepEqual(getGridContent().rows, [
        {
            pills: [{ title: "Task 7", level: 0, colSpan: "20 (1/2) -> 20" }],
        },
    ]);

    // move a pill in the next cell (+1 day)
    const { drop } = await dragPill("Task 7");
    await drop({ row: 1, column: 21, part: 2 });

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [{ title: "Task 7", level: 0, colSpan: "21 (1/2) -> 21" }],
        },
    ]);
});

QUnit.test("move a pill in the same row (with different timezone)", async (assert) => {
    assert.expect(5);

    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records[7].start = `${DST_DATES.winterToSummer.before} 05:00:00`;
    serverData.models.tasks.records[7].stop = `${DST_DATES.winterToSummer.before} 06:30:00`;

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
        async mockRPC(_route, { args, method }) {
            if (method === "write") {
                assert.step("write");
                assert.deepEqual(args, [
                    [8],
                    {
                        start: `${DST_DATES.winterToSummer.after} 04:00:00`,
                        stop: `${DST_DATES.winterToSummer.after} 05:30:00`,
                    },
                ]);
            }
        },
    });

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [{ title: "Task 8", level: 0, colSpan: "30 -> 30 (1/2)" }],
        },
    ]);

    // +1 day -> move beyond the DST switch
    const { drop } = await dragPill("Task 8");
    await drop({ row: 1, column: 31, part: 1 });

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [{ title: "Task 8", level: 0, colSpan: "31 -> 31 (1/2)" }],
        },
    ]);
    assert.verifySteps(["write"]);
});

QUnit.test("move a pill in another row", async (assert) => {
    assert.expect(4);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["project_id"],
        domain: [["id", "in", [1, 7]]],
        mockRPC(_route, { args, method }) {
            if (method === "write") {
                assert.deepEqual(args[0], [7], "should write on the correct record");
                assert.deepEqual(
                    args[1],
                    {
                        project_id: 1,
                        start: "2018-12-21 12:30:12",
                        stop: "2018-12-21 18:29:59",
                    },
                    "all modified fields should be correctly set"
                );
            }
        },
    });

    assert.deepEqual(getGridContent().rows, [
        {
            title: "Project 1",
            pills: [{ title: "Task 1", level: 0, colSpan: "01 -> 31" }],
        },
        {
            title: "Project 2",
            pills: [{ title: "Task 7", level: 0, colSpan: "20 (1/2) -> 20" }],
        },
    ]);

    // move a pill (task 7) in the other row and in the the next cell (+1 day)
    const { drop } = await dragPill("Task 7");
    await drop({ row: 1, column: 21, part: 2 });

    assert.deepEqual(getGridContent().rows, [
        {
            title: "Project 1",
            pills: [
                { title: "Task 1", level: 0, colSpan: "01 -> 31" },
                { title: "Task 7", level: 1, colSpan: "21 (1/2) -> 21" },
            ],
        },
    ]);
});

QUnit.test("copy a pill in another row", async (assert) => {
    assert.expect(6);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["project_id"],
        domain: [["id", "in", [1, 7, 9]]], // 9 will be the newly created record
        mockRPC(_route, { args, method }) {
            if (method === "copy") {
                assert.deepEqual(args[0], 7, "should copy the correct record");
                assert.deepEqual(
                    args[1],
                    {
                        start: "2018-12-21 12:30:12",
                        stop: "2018-12-21 18:29:59",
                        project_id: 1,
                    },
                    "should use the correct default values when copying"
                );
            }
        },
    });

    assert.deepEqual(getGridContent().rows, [
        {
            title: "Project 1",
            pills: [{ title: "Task 1", level: 0, colSpan: "01 -> 31" }],
        },
        {
            title: "Project 2",
            pills: [{ title: "Task 7", level: 0, colSpan: "20 (1/2) -> 20" }],
        },
    ]);

    await triggerEvent(window, null, "keydown", { key: "Control" });

    // move a pill (task 7) in the other row and in the the next cell (+1 day)
    const { drop, moveTo } = await dragPill("Task 7");
    await moveTo({ row: 1, column: 21, part: 2 });

    assert.hasClass(target.querySelector(SELECTORS.renderer), "o_copying");

    await triggerEvent(window, null, "keyup", { key: "Control" });

    assert.hasClass(target.querySelector(SELECTORS.renderer), "o_grabbing");

    await triggerEvent(window, null, "keydown", { key: "Control" });
    await drop();

    assert.deepEqual(getGridContent().rows, [
        {
            title: "Project 1",
            pills: [
                { title: "Task 1", level: 0, colSpan: "01 -> 31" },
                { title: "Task 7 (copy)", level: 1, colSpan: "21 (1/2) -> 21" },
            ],
        },
        {
            title: "Project 2",
            pills: [{ title: "Task 7", level: 0, colSpan: "20 (1/2) -> 20" }],
        },
    ]);
});

QUnit.test("move a pill in another row in multi-level grouped", async (assert) => {
    assert.expect(5);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["user_id", "project_id", "stage"],
        mockRPC(_route, { args, method }) {
            if (method === "write") {
                assert.deepEqual(
                    args,
                    [[7], { project_id: 1 }],
                    "should only write on user_id on the correct record"
                );
            }
        },
        domain: [["id", "in", [3, 7]]],
    });

    assert.containsOnce(target, `${SELECTORS.pillWrapper}${SELECTORS.draggable}`);
    assert.containsOnce(target, `${SELECTORS.pillWrapper}${SELECTORS.undraggable}`);
    assert.deepEqual(getGridContent().rows, [
        {
            title: "User 2",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "20 (1/2) -> 20" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            isGroup: true,
            pills: [{ title: "1", colSpan: "27 -> 31" }],
        },
        {
            title: "Cancelled",
            pills: [{ title: "Task 3", level: 0, colSpan: "27 -> 31" }],
        },
        {
            title: "Project 2",
            isGroup: true,
            pills: [{ title: "1", colSpan: "20 (1/2) -> 20" }],
        },
        {
            title: "Cancelled",
            pills: [{ title: "Task 7", level: 0, colSpan: "20 (1/2) -> 20" }],
        },
    ]);

    // move a pill (task 7) in the top-level group (User 2)
    const { drop } = await dragPill("Task 7");
    await drop({ row: 3, column: 20, part: 2 });

    assert.deepEqual(getGridContent().rows, [
        {
            title: "User 2",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "20 (1/2) -> 20" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "20 (1/2) -> 20" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Cancelled",
            pills: [
                { title: "Task 7", level: 0, colSpan: "20 (1/2) -> 20" },
                { title: "Task 3", level: 0, colSpan: "27 -> 31" },
            ],
        },
    ]);
});

QUnit.test("move a pill in another row in multi-level grouped (many2many case)", async (assert) => {
    assert.expect(5);

    const { tasks } = serverData.models;
    tasks.fields.user_ids = { string: "Assignees", type: "many2many", relation: "users" };
    tasks.records[1].user_ids = [1, 2];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["user_id", "project_id", "user_ids"],
        domain: [
            ["user_id", "=", 2],
            ["project_id", "=", 1],
        ],
        mockRPC(_route, { args, method }) {
            if (method === "write") {
                assert.deepEqual(args[0], [2], "should write on the correct record");
                assert.deepEqual(args[1], { user_ids: false }, "should write these changes");
            }
        },
    });

    // sanity check
    assert.deepEqual(getTexts(`${SELECTORS.pillWrapper}${SELECTORS.draggable}`), [
        "Task 2",
        "Task 2",
    ]);
    assert.deepEqual(getGridContent().rows, [
        {
            title: "User 2",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Undefined Assignees",
            pills: [{ title: "Task 3", level: 0, colSpan: "27 -> 31" }],
        },
        {
            title: "User 1",
            pills: [{ title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" }],
        },
        {
            title: "User 2",
            pills: [{ title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" }],
        },
    ]);

    // move a pill (first task 2) in "Undefined Assignees"
    const { drop } = await dragPill("Task 2", { nth: 1 });
    await drop({ row: 3, column: 17, part: 2 });

    assert.deepEqual(getGridContent().rows, [
        {
            title: "User 2",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Project 1",
            isGroup: true,
            pills: [
                { title: "1", colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "1", colSpan: "27 -> 31" },
            ],
        },
        {
            title: "Undefined Assignees",
            pills: [
                { title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "Task 3", level: 0, colSpan: "27 -> 31" },
            ],
        },
    ]);
});

QUnit.test("grey pills should not be resizable nor draggable", async (assert) => {
    assert.expect(4);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" color="color" />',
        groupBy: ["user_id", "project_id"],
        domain: [["id", "=", 7]],
    });

    const groupPill = target.querySelector(`${SELECTORS.pillWrapper}.o_gantt_group_pill`);
    assert.doesNotHaveClass(groupPill, CLASSES.resizable);
    assert.doesNotHaveClass(groupPill, CLASSES.draggable);

    const rowPill = target.querySelector(`${SELECTORS.pillWrapper}:not(.o_gantt_group_pill)`);
    assert.hasClass(rowPill, CLASSES.resizable);
    assert.hasClass(rowPill, CLASSES.draggable);
});

QUnit.test("should not be draggable when disable_drag_drop is set", async (assert) => {
    assert.expect(1);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" color="color" disable_drag_drop="1" />',
        groupBy: ["user_id", "project_id"],
        domain: [["id", "=", 7]],
    });

    assert.containsNone(target, SELECTORS.draggable);
});

QUnit.test("gantt_unavailability reloads when the view's scale changes", async (assert) => {
    let unavailabilityCallCount = 0;
    let unavailabilityScaleArg = "none";
    let reloadCount = 0;

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" display_unavailability="1" />',
        async mockRPC(_route, { args, method }) {
            if (method === "get_gantt_data") {
                reloadCount++;
            } else if (method === "gantt_unavailability") {
                unavailabilityCallCount++;
                unavailabilityScaleArg = args[2];
                return args[4];
            }
        },
    });

    assert.strictEqual(reloadCount, 1, "view should have loaded");
    assert.strictEqual(unavailabilityCallCount, 1, "view should have loaded unavailability");

    await setScale("week");
    assert.strictEqual(reloadCount, 2, "view should have reloaded when switching scale to week");
    assert.strictEqual(
        unavailabilityCallCount,
        2,
        "view should have reloaded when switching scale to week"
    );
    assert.strictEqual(
        unavailabilityScaleArg,
        "week",
        "unavailability should have been called with the week scale"
    );

    await setScale("month");
    assert.strictEqual(reloadCount, 3, "view should have reloaded when switching scale to month");
    assert.strictEqual(
        unavailabilityCallCount,
        3,
        "view should have reloaded when switching scale to month"
    );
    assert.strictEqual(
        unavailabilityScaleArg,
        "month",
        "unavailability should have been called with the month scale"
    );

    await setScale("year");
    assert.strictEqual(reloadCount, 4, "view should have reloaded when switching scale to year");
    assert.strictEqual(
        unavailabilityCallCount,
        4,
        "view should have reloaded when switching scale to year"
    );
    assert.strictEqual(
        unavailabilityScaleArg,
        "year",
        "unavailability should have been called with the year scale"
    );
});

QUnit.test("gantt_unavailability reload when period changes", async (assert) => {
    let unavailabilityCallCount = 0;
    let reloadCount = 0;

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" display_unavailability="1" />',
        async mockRPC(_route, { args, method }) {
            if (method === "get_gantt_data") {
                reloadCount++;
            } else if (method === "gantt_unavailability") {
                unavailabilityCallCount++;
                return args[4];
            }
        },
    });

    assert.strictEqual(reloadCount, 1, "view should have loaded");
    assert.strictEqual(unavailabilityCallCount, 1, "view should have loaded unavailability");

    await click(target, SELECTORS.nextButton);
    assert.strictEqual(reloadCount, 2, "view should have reloaded when clicking next");
    assert.strictEqual(
        unavailabilityCallCount,
        2,
        "view should have reloaded unavailability when clicking next"
    );

    await click(target, SELECTORS.prevButton);
    assert.strictEqual(reloadCount, 3, "view should have reloaded when clicking prev");
    assert.strictEqual(
        unavailabilityCallCount,
        3,
        "view should have reloaded unavailability when clicking prev"
    );
});

QUnit.test(
    "gantt_unavailability should not reload when period changes if display_unavailability is not set",
    async (assert) => {
        let unavailabilityCallCount = 0;
        let reloadCount = 0;

        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: '<gantt date_start="start" date_stop="stop" />',
            async mockRPC(_route, { args, method }) {
                if (method === "get_gantt_data") {
                    reloadCount++;
                } else if (method === "gantt_unavailability") {
                    unavailabilityCallCount++;
                    return {};
                }
            },
        });

        assert.strictEqual(reloadCount, 1, "view should have loaded");
        assert.strictEqual(
            unavailabilityCallCount,
            0,
            "view should not have loaded unavailability"
        );

        await click(target, SELECTORS.nextButton);
        assert.strictEqual(reloadCount, 2, "view should have reloaded when clicking next");
        assert.strictEqual(
            unavailabilityCallCount,
            0,
            "view should not have reloaded unavailability when clicking next"
        );

        await click(target, SELECTORS.prevButton);
        assert.strictEqual(reloadCount, 3, "view should have reloaded when clicking prev");
        assert.strictEqual(
            unavailabilityCallCount,
            0,
            "view should not have reloaded unavailability when clicking prev"
        );
    }
);

QUnit.test("close tooltip when drag pill", async (assert) => {
    serverData.models.tasks.records[1].start = "2018-12-16 03:00:00";
    serverData.views["tasks,false,form"] = "<form/>";

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt default_scale="week" date_start="start" date_stop="stop" />',
    });

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [
                {
                    title: "Task 1",
                    colSpan: "Sunday, 16 -> Saturday, 22",
                    level: 0,
                },
                {
                    title: "Task 2",
                    colSpan: "Sunday, 16 -> Saturday, 22 (1/2)",
                    level: 1,
                },
                {
                    title: "Task 4",
                    colSpan: "Thursday, 20 -> Thursday, 20 (1/2)",
                    level: 2,
                },
                {
                    title: "Task 7",
                    colSpan: "Thursday, 20 (1/2) -> Thursday, 20",
                    level: 2,
                },
            ],
        },
    ]);

    // open popover
    await click(getPill("Task 4"));
    assert.containsOnce(target, ".o_popover");

    // enable the drag feature and move the pill
    const { moveTo } = await dragPill("Task 4");
    assert.containsOnce(
        target,
        ".o_popover",
        "popover should is still opened as the pill did not move yet"
    );
    await moveTo({ pill: "Task 2" });
    // check popover
    assert.containsNone(target, ".o_popover", "popover should have been closed");
});

QUnit.test("drag&drop on other pill in grouped view", async (assert) => {
    serverData.models.tasks.records[0].start = "2018-12-16 05:00:00";
    serverData.models.tasks.records[0].stop = "2018-12-16 07:00:00";
    serverData.models.tasks.records[1].stop = "2018-12-17 13:00:00";
    serverData.views["tasks,false,form"] = `<form />`;

    const def = makeDeferred();
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt default_scale="week" date_start="start" date_stop="stop" />',
        groupBy: ["project_id"],
        async mockRPC(_route, { method }) {
            if (method === "write") {
                await def;
            }
        },
    });

    assert.deepEqual(getGridContent().rows, [
        {
            title: "Project 1",
            pills: [
                { title: "Task 1", level: 0, colSpan: "Sunday, 16 -> Sunday, 16 (1/2)" },
                { title: "Task 2", level: 0, colSpan: "Monday, 17 (1/2) -> Monday, 17" },
                { title: "Task 4", level: 0, colSpan: "Thursday, 20 -> Thursday, 20 (1/2)" },
            ],
        },
        {
            title: "Project 2",
            pills: [{ title: "Task 7", level: 0, colSpan: "Thursday, 20 (1/2) -> Thursday, 20" }],
        },
    ]);

    await click(getPill("Task 2"));

    assert.containsOnce(target, ".o_popover");

    const { drop } = await dragPill("Task 2");
    await drop({ pill: "Task 1" });

    await click(document.body); // To simulate the full 'pointerup' sequence

    def.resolve();
    await nextTick();

    assert.containsNone(document.body, ".popover");
    assert.deepEqual(getGridContent().rows, [
        {
            title: "Project 1",
            pills: [
                { title: "Task 2", level: 0, colSpan: "Sunday, 16 -> Sunday, 16 (1/2)" },
                { title: "Task 1", level: 1, colSpan: "Sunday, 16 -> Sunday, 16 (1/2)" },
                { title: "Task 4", level: 0, colSpan: "Thursday, 20 -> Thursday, 20 (1/2)" },
            ],
        },
        {
            title: "Project 2",
            pills: [{ title: "Task 7", level: 0, colSpan: "Thursday, 20 (1/2) -> Thursday, 20" }],
        },
    ]);
});

// ATTRIBUTES TESTS

QUnit.test("create attribute", async (assert) => {
    serverData.views = {
        "tasks,false,list": '<tree><field name="name"/></tree>',
        "tasks,false,search": '<search><field name="name"/></search>',
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" create="0" />',
    });
    assert.containsNone(target, ".o_dialog");
    await hoverGridCell(1, 1);
    await clickCell(1, 1);
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector(".modal-title").textContent, "Plan");
    assert.containsNone(target, ".o_create_button");
});

QUnit.test("plan attribute", async (assert) => {
    serverData.views = {
        "tasks,false,form": `<form><field name="name"/></form>`,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" plan="0" />',
    });
    assert.containsNone(target, ".o_dialog");
    await hoverGridCell(1, 1);
    await clickCell(1, 1);
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector(".modal-title").textContent, "Create");
});

QUnit.test("edit attribute", async (assert) => {
    serverData.views = {
        "tasks,false,form": `<form><field name="name"/></form>`,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" edit="0" />',
    });
    assert.containsNone(target, SELECTORS.resizable);
    assert.containsNone(target, SELECTORS.draggable);

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [
                { title: "Task 5", level: 0, colSpan: "01 -> 04 (1/2)" },
                { title: "Task 1", level: 1, colSpan: "01 -> 31" },
                { title: "Task 2", level: 0, colSpan: "17 (1/2) -> 22 (1/2)" },
                { title: "Task 4", level: 2, colSpan: "20 -> 20 (1/2)" },
                { title: "Task 7", level: 2, colSpan: "20 (1/2) -> 20" },
                { title: "Task 3", level: 0, colSpan: "27 -> 31" },
            ],
        },
    ]);

    await click(getPill("Task 1"));
    const popoverButton = target.querySelector(".o_popover button.btn-primary");
    assert.strictEqual(popoverButton.innerText.toUpperCase(), "VIEW");
    await click(popoverButton);
    assert.containsOnce(target, ".modal .o_form_readonly");
});

QUnit.test("total_row attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" total_row="1" />',
    });

    const { rows } = getGridContent();
    assert.deepEqual(rows, [
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
                {
                    colSpan: "01 -> 31",
                    level: 1,
                    title: "Task 1",
                },
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "20 -> 20 (1/2)",
                    level: 2,
                    title: "Task 4",
                },
                {
                    colSpan: "20 (1/2) -> 20",
                    level: 2,
                    title: "Task 7",
                },
                {
                    colSpan: "27 -> 31",
                    level: 0,
                    title: "Task 3",
                },
            ],
        },
        {
            isTotalRow: true,
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "04 (1/2) -> 17 (1/2)",
                    level: 0,
                    title: "1",
                },
                {
                    colSpan: "17 (1/2) -> 19",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "20 -> 20 (1/2)",
                    level: 0,
                    title: "3",
                },
                {
                    colSpan: "20 (1/2) -> 20",
                    level: 0,
                    title: "3",
                },
                {
                    colSpan: "21 -> 22 (1/2)",
                    level: 0,
                    title: "2",
                },
                {
                    colSpan: "22 (1/2) -> 26",
                    level: 0,
                    title: "1",
                },
                {
                    colSpan: "27 -> 31",
                    level: 0,
                    title: "2",
                },
            ],
        },
    ]);
});

QUnit.test("default_scale attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="day" />',
    });
    assert.strictEqual(getActiveScale(), "Day");
    const content = getGridContent(target);
    assert.strictEqual(content.range, "Thursday, December 20, 2018");
    assert.strictEqual(content.columnHeaders.length, 24);
});

QUnit.test("scales attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" scales="month,day,trololo" />',
    });
    await click(target, ".scale_button_selection");
    const availableScales = getTexts(".dropdown-item");
    assert.deepEqual(availableScales, ["Month", "Day"]);
    assert.strictEqual(getActiveScale(), "Month");
});

QUnit.test("precision attribute", async (assert) => {
    assert.expect(4);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                precision="{'day': 'hour:quarter', 'week': 'day:half', 'month': 'day', 'year': 'month:quarter'}"
                default_scale="day"
            />
        `,
        domain: [["id", "=", 7]],
        async mockRPC(_route, { method, args }) {
            if (method === "write") {
                assert.step(JSON.stringify(args));
            }
        },
    });

    // resize of a quarter
    const drop = await resizePill(getPillWrapper("Task 7"), "end", 0.25, false);

    const badge = target.querySelector(SELECTORS.resizeBadge);
    assert.strictEqual(badge.innerText, "+15 minutes");

    // manually trigger the drop to trigger a write
    await drop();

    assert.containsNone(target, SELECTORS.resizeBadge);
    assert.verifySteps([JSON.stringify([[7], { stop: "2018-12-20 18:44:59" }])]);
});

QUnit.test("progress attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt string="Tasks" date_start="start" date_stop="stop" progress="progress" />',
        groupBy: ["project_id"],
    });

    assert.containsN(target, `${SELECTORS.pill} .o_gantt_progress`, 4);
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.pill)].map((el) => {
            return {
                text: el.innerText,
                progress: el.querySelector(".o_gantt_progress")?.style?.width || null,
            };
        }),
        [
            { text: "Task 1", progress: null },
            { text: "Task 2", progress: "30%" },
            { text: "Task 4", progress: null },
            { text: "Task 3", progress: "60%" },
            { text: "Task 5", progress: "100%" },
            { text: "Task 7", progress: "80%" },
        ]
    );
});

QUnit.test("form_view_id attribute", async (assert) => {
    serverData.views = {
        "tasks,42,form": `<form><field name="name"/></form>`,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt string="Tasks" date_start="start" date_stop="stop" form_view_id="42"/>',
        groupBy: ["project_id"],
        mockRPC(_, { method, kwargs }) {
            if (method === "get_views") {
                assert.step(`get_views: ${JSON.stringify(kwargs.views)}`);
            }
        },
    });
    await click($(SELECTORS.addButton + ":visible").get(0));
    assert.containsOnce(target, ".modal .o_form_view");
    assert.verifySteps([
        `get_views: [[100000001,"gantt"],[100000002,"search"]]`, // initial get_views
        `get_views: [[42,"form"]]`, // get_views when form view dialog opens
    ]);
});

QUnit.test("decoration attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt date_start="start" date_stop="stop" decoration-info="stage == 'todo'">
                <field name="stage"/>
            '</gantt>
        `,
    });
    assert.hasClass(getPill("Task 1"), "decoration-info");
    assert.doesNotHaveClass(getPill("Task 2"), "decoration-info");
});

QUnit.test("decoration attribute with date", async (assert) => {
    patchDate(2018, 11, 19, 12, 0, 0);

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" decoration-danger="start &lt; today"/>`,
    });

    assert.hasClass(getPill("Task 1"), "decoration-danger");
    assert.hasClass(getPill("Task 2"), "decoration-danger");
    assert.hasClass(getPill("Task 5"), "decoration-danger");
    assert.doesNotHaveClass(getPill("Task 3"), "decoration-danger");
    assert.doesNotHaveClass(getPill("Task 4"), "decoration-danger");
    assert.doesNotHaveClass(getPill("Task 7"), "decoration-danger");
});

QUnit.test("consolidation feature", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                consolidation="progress"
                consolidation_max="{'user_id': 100}"
                consolidation_exclude="exclude"
                progress="progress"
            />
        `,
        groupBy: ["user_id", "project_id", "stage"],
    });

    const { rows } = getGridContent();

    assert.strictEqual(rows.length, 18);
    assert.strictEqual(rows.filter((r) => r.isGroup).length, 12);
    assert.containsOnce(target, ".o_gantt_row_headers");

    // Check grouped rows
    assert.ok(rows[0].isGroup);
    assert.strictEqual(rows[0].title, "User 1");

    assert.ok(rows[9].isGroup);
    assert.strictEqual(rows[9].title, "User 2");

    // Consolidation
    // 0 over the size of Task 5 (Task 5 is 100 but is excluded!) then 0 over the rest of Task 1, cut by Task 4 which has progress 0
    assert.deepEqual(rows[0].pills, [
        { colSpan: "01 -> 04 (1/2)", title: "0" },
        { colSpan: "04 (1/2) -> 19", title: "0" },
        { colSpan: "20 -> 20 (1/2)", title: "0" },
        { colSpan: "20 (1/2) -> 31", title: "0" },
    ]);

    // 30 over Task 2 until Task 7 then 110 (Task 2 (30) + Task 7 (80)) then 30 again until end of task 2 then 60 over Task 3
    assert.deepEqual(rows[9].pills, [
        { colSpan: "17 (1/2) -> 20 (1/2)", title: "30" },
        { colSpan: "20 (1/2) -> 20", title: "110" },
        { colSpan: "21 -> 22 (1/2)", title: "30" },
        { colSpan: "27 -> 31", title: "60" },
    ]);

    const withStatus = [];
    for (const el of target.querySelectorAll(".o_gantt_consolidated_pill")) {
        if (el.classList.contains("bg-success") || el.classList.contains("bg-danger")) {
            withStatus.push({
                title: el.title,
                danger: el.classList.contains("border-danger"),
            });
        }
    }

    assert.deepEqual(withStatus, [
        { title: "0", danger: false },
        { title: "0", danger: false },
        { title: "0", danger: false },
        { title: "0", danger: false },
        { title: "30", danger: false },
        { title: "110", danger: true },
        { title: "30", danger: false },
        { title: "60", danger: false },
    ]);
});

QUnit.test("consolidation feature (single level)", async (assert) => {
    serverData.views = {
        "tasks,false,form": `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
                <field name="project_id"/>
            </form>
        `,
    };

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt
            date_start="start"
            date_stop="stop"
            consolidation="progress"
            consolidation_max="{'user_id': 100}"
            consolidation_exclude="exclude"
            />`,
        groupBy: ["user_id"],
    });

    const { rows, range } = getGridContent();

    assert.strictEqual(range, "December 2018", "should have a range");
    assert.containsOnce(
        target,
        ".o_gantt_button_expand_rows",
        "the expand button should be visible"
    );
    assert.deepEqual(rows, [
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    title: "0",
                },
                {
                    colSpan: "04 (1/2) -> 19",
                    title: "0",
                },
                {
                    colSpan: "20 -> 20 (1/2)",
                    title: "0",
                },
                {
                    colSpan: "20 (1/2) -> 31",
                    title: "0",
                },
            ],
            title: "User 1",
        },
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
                {
                    colSpan: "01 -> 31",
                    level: 1,
                    title: "Task 1",
                },
                {
                    colSpan: "20 -> 20 (1/2)",
                    level: 0,
                    title: "Task 4",
                },
            ],
            title: "",
        },
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "17 (1/2) -> 20 (1/2)",
                    title: "30",
                },
                {
                    colSpan: "20 (1/2) -> 20",
                    title: "110",
                },
                {
                    colSpan: "21 -> 22 (1/2)",
                    title: "30",
                },
                {
                    colSpan: "27 -> 31",
                    title: "60",
                },
            ],
            title: "User 2",
        },
        {
            pills: [
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "20 (1/2) -> 20",
                    level: 1,
                    title: "Task 7",
                },
                {
                    colSpan: "27 -> 31",
                    level: 0,
                    title: "Task 3",
                },
            ],
            title: "",
        },
    ]);
});

QUnit.test("color attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" color="color" />',
    });
    assert.hasClass(getPill("Task 1"), "o_gantt_color_0");
    assert.hasClass(getPill("Task 2"), "o_gantt_color_2");
});

QUnit.test("color attribute in multi-level grouped", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" color="color" />',
        groupBy: ["user_id", "project_id"],
        domain: [["id", "=", 1]],
    });
    assert.doesNotHaveClass(
        target.querySelector(`${SELECTORS.pill}.o_gantt_consolidated_pill`),
        "o_gantt_color_0"
    );
    assert.hasClass(
        target.querySelector(`${SELECTORS.pill}:not(.o_gantt_consolidated_pill)`),
        "o_gantt_color_0"
    );
});

QUnit.test("color attribute on a many2one", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" color="project_id" />',
    });
    assert.hasClass(getPill("Task 1"), "o_gantt_color_1");
    assert.containsN(target, `${SELECTORS.pill}.o_gantt_color_1`, 4);
    assert.containsN(target, `${SELECTORS.pill}.o_gantt_color_2`, 2);
});

QUnit.test('Today style with unavailabilities ("week": "day:half")', async (assert) => {
    const unavailabilities = [
        {
            start: "2018-12-18 10:00:00",
            stop: "2018-12-20 14:00:00",
        },
    ];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1"
                    default_scale="week" scales="week" precision="{'week': 'day:half'}"/>`,
        mockRPC(_route, { args, method }) {
            if (method === "gantt_unavailability") {
                const rows = args[4];
                return rows.map((row) => Object.assign(row, { unavailabilities }));
            }
        },
    });

    // Normal day / unavailability
    assert.deepEqual(getCellColorProperties(1, 3), [
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);

    // Full unavailability
    assert.deepEqual(getCellColorProperties(1, 4), ["--Gantt__DayOff-background-color"]);

    // Unavailability / today
    assert.hasClass(getCell(1, 5), "o_gantt_today");
    assert.deepEqual(getCellColorProperties(1, 5), [
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOffToday-background-color",
    ]);
});

QUnit.test("Today style of group rows", async (assert) => {
    const unavailabilities = [
        {
            start: "2018-12-18 10:00:00",
            stop: "2018-12-20 14:00:00",
        },
    ];
    serverData.models.tasks.records = [serverData.models.tasks.records[3]]; // id: 4

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1"
                    default_scale="week" scales="week" precision="{'week': 'day:half'}"/>`,
        groupBy: ["user_id", "project_id"],
        mockRPC(_, { args, method }) {
            if (method === "gantt_unavailability") {
                const rows = args[4];
                for (const r of rows) {
                    r.unavailabilities = unavailabilities;
                }
                return rows;
            }
        },
    });

    // Normal group cell: open
    let cell4 = getCell(1, 4, { ignoreHoverableClass: true });
    assert.doesNotHaveClass(cell4, "o_gantt_today");
    assert.hasClass(cell4, "o_group_open");
    let cell4ComputedBackGround = window.getComputedStyle(cell4).background;
    assert.ok(
        cell4ComputedBackGround.includes("linear-gradient(rgb(249, 250, 251), rgb(234, 237, 241))")
    );
    assert.notOk(cell4ComputedBackGround.includes("rgb(252, 250, 243)"));

    // Today group cell: open
    let cell5 = getCell(1, 5, { ignoreHoverableClass: true });
    assert.hasClass(cell5, "o_gantt_today");
    assert.hasClass(cell5, "o_group_open");
    let cell5ComputedBackGround = window.getComputedStyle(cell5).background;
    assert.ok(
        cell5ComputedBackGround.includes("linear-gradient(rgb(249, 250, 251), rgb(234, 237, 241))")
    );
    assert.notOk(cell5ComputedBackGround.includes("rgb(252, 250, 243)"));

    await click(target.querySelector(SELECTORS.group)); // fold group

    // Normal group cell: closed

    cell4 = getCell(1, 4, { ignoreHoverableClass: true });
    assert.doesNotHaveClass(cell4, "o_gantt_today");
    assert.doesNotHaveClass(cell4, "o_group_open");
    cell4ComputedBackGround = window.getComputedStyle(cell4).background;
    assert.ok(
        cell4ComputedBackGround.includes("linear-gradient(rgb(234, 237, 241), rgb(249, 250, 251))")
    );
    assert.notOk(cell4ComputedBackGround.includes("rgb(252, 250, 243)"));

    // Today group cell: closed
    cell5 = getCell(1, 5, { ignoreHoverableClass: true });
    assert.hasClass(cell5, "o_gantt_today");
    assert.doesNotHaveClass(cell5, "o_group_open");
    cell5ComputedBackGround = window.getComputedStyle(cell5).background;
    assert.notOk(
        cell5ComputedBackGround.includes("linear-gradient(rgb(234, 237, 241), rgb(249, 250, 251))")
    );
    assert.ok(cell5ComputedBackGround.includes("rgb(252, 250, 243)"));
});

QUnit.test("style without unavailabilities", async (assert) => {
    patchDate(2018, 11, 5, 2, 0, 0);
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" display_unavailability="1" />',
        async mockRPC(_, { method, args }) {
            if (method === "gantt_unavailability") {
                return args[4];
            }
        },
    });
    const cell5 = getCell(1, 5);
    assert.hasClass(cell5, "o_gantt_today");
    assert.hasAttrValue(cell5, "style", "grid-column:9 / span 2;grid-row:1 / span 31;"); // span 31 = 3 level * 9 per level + 4 for general space
    const cell6 = getCell(1, 6);
    assert.hasAttrValue(cell6, "style", "grid-column:11 / span 2;grid-row:1 / span 31;");
});

QUnit.test('Unavailabilities ("month": "day:half")', async (assert) => {
    patchDate(2018, 11, 5, 2, 0, 0);
    const unavailabilities = [
        {
            start: "2018-12-05 09:30:00",
            stop: "2018-12-07 08:00:00",
        },
        {
            start: "2018-12-16 09:00:00",
            stop: "2018-12-18 13:00:00",
        },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" display_unavailability="1" />',
        async mockRPC(_, { method, args, model }) {
            if (method === "gantt_unavailability") {
                assert.strictEqual(model, "tasks");
                assert.strictEqual(args[0], "2018-11-30 23:00:00");
                assert.strictEqual(args[1], "2018-12-31 22:59:59");
                const rows = args[4];
                for (const r of rows) {
                    r.unavailabilities = unavailabilities;
                }
                return rows;
            }
        },
    });
    assert.hasClass(getCell(1, 5), "o_gantt_today");
    assert.deepEqual(getCellColorProperties(1, 5), [
        "--Gantt__DayOffToday-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 6), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 7), []);
    assert.deepEqual(getCellColorProperties(1, 16), [
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 17), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 18), [
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
    ]);
});

QUnit.test('Unavailabilities ("day": "hours:quarter")', async (assert) => {
    serverData.models.tasks.records = [];
    const unavailabilities = [
        // in utc
        {
            start: "2018-12-20 08:15:00",
            stop: "2018-12-20 08:30:00",
        },
        {
            start: "2018-12-20 10:35:00",
            stop: "2018-12-20 12:29:00",
        },
        {
            start: "2018-12-20 20:15:00",
            stop: "2018-12-20 20:50:00",
        },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="1"
                    default_scale="day" scales="day" precision="{'day': 'hours:quarter'}"/>`,
        async mockRPC(_, { method, args }) {
            if (method === "gantt_unavailability") {
                const rows = args[4];
                for (const r of rows) {
                    r.unavailabilities = unavailabilities;
                }
                return rows;
            }
        },
    });
    assert.deepEqual(getCellColorProperties(1, 10), [
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 12), [
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 13), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 14), [
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
        "--Gantt__Day-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 22), [
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
    ]);
});

QUnit.test('Unavailabilities ("month": "day:half")', async (assert) => {
    assert.expect(10);
    patchDate(2018, 11, 5, 2, 0, 0);
    const unavailabilities = [
        { start: "2018-12-05 09:30:00", stop: "2018-12-07 08:00:00" },
        { start: "2018-12-16 09:00:00", stop: "2018-12-18 13:00:00" },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" display_unavailability="1" />',
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_unavailability") {
                assert.strictEqual(model, "tasks");
                assert.strictEqual(args[0], "2018-11-30 23:00:00");
                assert.strictEqual(args[1], "2018-12-31 22:59:59");
                const rows = args[4];
                for (const r of rows) {
                    r.unavailabilities = unavailabilities;
                }
                return rows;
            }
        },
    });
    assert.hasClass(getCell(1, 5), "o_gantt_today");
    assert.deepEqual(getCellColorProperties(1, 5), [
        "--Gantt__DayOffToday-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 6), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 7), []);
    assert.deepEqual(getCellColorProperties(1, 16), [
        "--Gantt__Day-background-color",
        "--Gantt__DayOff-background-color",
    ]);
    assert.deepEqual(getCellColorProperties(1, 17), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 18), [
        "--Gantt__DayOff-background-color",
        "--Gantt__Day-background-color",
    ]);
});

QUnit.test("offset attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" offset="-4" default_scale="day"/>',
    });

    const { range } = getGridContent();
    assert.strictEqual(
        range,
        "Sunday, December 16, 2018",
        "gantt view should be set to 4 days before initial date"
    );
});

QUnit.test("default_group_by attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_group_by="user_id" />',
    });

    const { rows } = getGridContent();
    assert.deepEqual(
        rows,
        [
            {
                title: "User 1",
                pills: [
                    {
                        colSpan: "01 -> 04 (1/2)",
                        level: 0,
                        title: "Task 5",
                    },
                    {
                        colSpan: "01 -> 31",
                        level: 1,
                        title: "Task 1",
                    },
                    {
                        colSpan: "20 -> 20 (1/2)",
                        level: 0,
                        title: "Task 4",
                    },
                ],
            },
            {
                title: "User 2",
                pills: [
                    {
                        colSpan: "17 (1/2) -> 22 (1/2)",
                        level: 0,
                        title: "Task 2",
                    },
                    {
                        colSpan: "20 (1/2) -> 20",
                        level: 1,
                        title: "Task 7",
                    },
                    {
                        colSpan: "27 -> 31",
                        level: 0,
                        title: "Task 3",
                    },
                ],
            },
        ],
        "should be grouped by user"
    );
});

QUnit.test("default_group_by attribute with groupBy", async (assert) => {
    // The default_group_by attribute should be ignored if a groupBy is given.
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_group_by="user_id" />',
        groupBy: ["project_id"],
    });

    const { rows } = getGridContent();
    assert.deepEqual(
        rows,
        [
            {
                title: "Project 1",
                pills: [
                    {
                        colSpan: "01 -> 31",
                        level: 0,
                        title: "Task 1",
                    },
                    {
                        colSpan: "17 (1/2) -> 22 (1/2)",
                        level: 1,
                        title: "Task 2",
                    },
                    {
                        colSpan: "20 -> 20 (1/2)",
                        level: 2,
                        title: "Task 4",
                    },
                    {
                        colSpan: "27 -> 31",
                        level: 1,
                        title: "Task 3",
                    },
                ],
            },
            {
                title: "Project 2",
                pills: [
                    {
                        colSpan: "01 -> 04 (1/2)",
                        level: 0,
                        title: "Task 5",
                    },
                    {
                        colSpan: "20 (1/2) -> 20",
                        level: 0,
                        title: "Task 7",
                    },
                ],
            },
        ],
        "should be grouped by project"
    );
});

QUnit.test("default_group_by attribute with 2 fields", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_group_by="user_id,project_id"/>',
    });

    const { rows } = getGridContent();
    assert.deepEqual(
        rows,
        [
            {
                title: "User 1",
                isGroup: true,
                pills: [
                    {
                        colSpan: "01 -> 04 (1/2)",
                        title: "2",
                    },
                    {
                        colSpan: "04 (1/2) -> 19",
                        title: "1",
                    },
                    {
                        colSpan: "20 -> 20 (1/2)",
                        title: "2",
                    },
                    {
                        colSpan: "20 (1/2) -> 31",
                        title: "1",
                    },
                ],
            },
            {
                title: "Project 1",
                pills: [
                    {
                        colSpan: "01 -> 31",
                        level: 0,
                        title: "Task 1",
                    },
                    {
                        colSpan: "20 -> 20 (1/2)",
                        level: 1,
                        title: "Task 4",
                    },
                ],
            },
            {
                title: "Project 2",
                pills: [
                    {
                        colSpan: "01 -> 04 (1/2)",
                        level: 0,
                        title: "Task 5",
                    },
                ],
            },
            {
                title: "User 2",
                isGroup: true,
                pills: [
                    {
                        colSpan: "17 (1/2) -> 20 (1/2)",
                        title: "1",
                    },
                    {
                        colSpan: "20 (1/2) -> 20",
                        title: "2",
                    },
                    {
                        colSpan: "21 -> 22 (1/2)",
                        title: "1",
                    },
                    {
                        colSpan: "27 -> 31",
                        title: "1",
                    },
                ],
            },
            {
                title: "Project 1",
                pills: [
                    {
                        colSpan: "17 (1/2) -> 22 (1/2)",
                        level: 0,
                        title: "Task 2",
                    },
                    {
                        colSpan: "27 -> 31",
                        level: 0,
                        title: "Task 3",
                    },
                ],
            },
            {
                title: "Project 2",
                pills: [
                    {
                        colSpan: "20 (1/2) -> 20",
                        level: 0,
                        title: "Task 7",
                    },
                ],
            },
        ],
        "there should be 2 rows and 4 sub rows."
    );
});

QUnit.test("dynamic_range attribute", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_group_by="user_id" dynamic_range="1" default_scale="month"/>',
    });

    const { columnHeaders } = getGridContent();
    assert.deepEqual(
        columnHeaders,
        [
            "20",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "29",
            "30",
            "31",
            "01",
            "02",
            "03",
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
        ],
        "should start at the first record, not at the beginning of the month"
    );
});

// CONCURRENCY TESTS

QUnit.test("concurrent scale switches return in inverse order", async (assert) => {
    let model;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            model = this.model;
            onPatched(() => {
                assert.step("patched");
            });
        },
    });

    let firstReloadProm = null;
    let reloadProm = null;
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        async mockRPC(_, { method }) {
            if (method === "get_gantt_data") {
                await reloadProm;
            }
        },
    });

    let content = getGridContent();

    assert.strictEqual(getActiveScale(), "Month");
    assert.strictEqual(content.range, "December 2018");
    assert.strictEqual(model.data.records.length, 6);

    // switch to 'week' scale (this rpc will be delayed)
    firstReloadProm = makeDeferred();
    reloadProm = firstReloadProm;
    await setScale("week");

    content = getGridContent();

    assert.strictEqual(getActiveScale(), "Month");
    assert.strictEqual(content.range, "December 2018");
    assert.strictEqual(model.data.records.length, 6);

    // switch to 'year' scale
    reloadProm = null;
    await setScale("year");

    content = getGridContent();

    assert.strictEqual(getActiveScale(), "Year");
    assert.strictEqual(content.range, "2018");
    assert.strictEqual(model.data.records.length, 7);

    firstReloadProm.resolve();
    await nextTick();

    content = getGridContent();

    assert.strictEqual(getActiveScale(), "Year");
    assert.strictEqual(content.range, "2018");
    assert.strictEqual(model.data.records.length, 7);

    assert.verifySteps(["patched"]); // should only be patched once
});

QUnit.test("concurrent scale switches return with gantt_unavailability", async (assert) => {
    const unavailabilities = [
        [{ start: "2018-12-10 23:00:00", stop: "2018-12-11 23:00:00" }],
        [{ start: "2018-07-30 23:00:00", stop: "2018-08-31 23:00:00" }],
    ];

    let model;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            model = this.model;
            onPatched(() => {
                assert.step("patched");
            });
        },
    });

    let firstReloadProm = null;
    let reloadProm = null;
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" display_unavailability="true" />',
        async mockRPC(_, { method, args }) {
            if (method === "gantt_unavailability") {
                await reloadProm;
                const rows = args[4];
                return rows.map((row) =>
                    Object.assign(row, {
                        unavailabilities: unavailabilities.shift(),
                    })
                );
            }
        },
    });

    let content = getGridContent();

    assert.strictEqual(getActiveScale(), "Month");
    assert.strictEqual(content.range, "December 2018");
    assert.strictEqual(model.data.records.length, 6);
    assert.deepEqual(getCellColorProperties(1, 8), []);
    assert.deepEqual(getCellColorProperties(1, 11), ["--Gantt__DayOff-background-color"]);

    // switch to 'week' scale (this rpc will be delayed)
    firstReloadProm = makeDeferred();
    reloadProm = firstReloadProm;
    await setScale("week");

    content = getGridContent();

    assert.strictEqual(getActiveScale(), "Month");
    assert.strictEqual(content.range, "December 2018");
    assert.strictEqual(model.data.records.length, 6);
    assert.deepEqual(getCellColorProperties(1, 8), []);
    assert.deepEqual(getCellColorProperties(1, 11), ["--Gantt__DayOff-background-color"]);

    // switch to 'year' scale
    reloadProm = null;
    await setScale("year");

    content = getGridContent();

    assert.strictEqual(getActiveScale(), "Year");
    assert.strictEqual(content.range, "2018");
    assert.strictEqual(model.data.records.length, 7);
    assert.deepEqual(getCellColorProperties(1, 8), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 11), []);

    firstReloadProm.resolve();
    await nextTick();

    content = getGridContent();

    assert.strictEqual(getActiveScale(), "Year");
    assert.strictEqual(content.range, "2018");
    assert.strictEqual(model.data.records.length, 7);
    assert.deepEqual(getCellColorProperties(1, 8), ["--Gantt__DayOff-background-color"]);
    assert.deepEqual(getCellColorProperties(1, 11), []);

    assert.verifySteps(["patched"]); // should only be patched once
});

QUnit.test("concurrent focusDate selections", async (assert) => {
    let reloadProm = null;
    let firstReloadProm = null;
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        async mockRPC(_, { method }) {
            if (method === "get_gantt_data") {
                await reloadProm;
            }
        },
    });

    let content = getGridContent();

    assert.strictEqual(getActiveScale(), "Month");
    assert.strictEqual(content.range, "December 2018");

    reloadProm = makeDeferred();
    firstReloadProm = reloadProm;
    await click(target, SELECTORS.nextButton);
    reloadProm = null;
    await click(target, SELECTORS.nextButton);

    firstReloadProm.resolve();
    await nextTick();

    content = getGridContent();
    assert.strictEqual(content.range, "February 2019");
});

QUnit.test("concurrent pill resize and groupBy change", async (assert) => {
    let awaitWriteDef = false;
    const writeDef = makeDeferred();
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        searchViewArch: `
            <search>
                <filter name="group_by" string="Project" domain="[]" context="{ 'group_by': 'project_id' }"/>
            </search>
        `,
        domain: [["id", "in", [2, 5]]],
        async mockRPC(_route, { args, method }) {
            assert.step(JSON.stringify([method, args]));
            if (method === "write" && awaitWriteDef) {
                await writeDef;
            }
        },
    });

    assert.verifySteps([JSON.stringify(["get_views", []]), JSON.stringify(["get_gantt_data", []])]);

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
            ],
        },
    ]);

    // resize "Task 2" to 1 cell smaller (-1 day) ; this RPC will be delayed
    awaitWriteDef = true;
    await resizePill(getPillWrapper("Task 2"), "end", -1);

    assert.verifySteps([JSON.stringify(["write", [[2], { stop: "2018-12-21 06:29:59" }]])]);

    await toggleSearchBarMenu(target);
    await toggleMenuItem(target, "Project");

    assert.verifySteps([JSON.stringify(["get_gantt_data", []])]);

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Project 1",
        },
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
            ],
            title: "Project 2",
        },
    ]);

    writeDef.resolve();
    await nextTick();

    assert.verifySteps([JSON.stringify(["get_gantt_data", []])]);

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [
                {
                    colSpan: "17 (1/2) -> 21 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Project 1",
        },
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
            ],
            title: "Project 2",
        },
    ]);
});

QUnit.test("concurrent pill resizes return in inverse order", async (assert) => {
    assert.expect(7);

    let awaitWriteDef = false;
    const writeDef = makeDeferred();
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 2]],
        async mockRPC(_route, { args, method }) {
            assert.step(JSON.stringify([method, args]));
            if (method === "write" && awaitWriteDef) {
                await writeDef;
            }
        },
    });

    // resize to 1 cell smaller (-1 day) ; this RPC will be delayed
    awaitWriteDef = true;
    await resizePill(getPillWrapper("Task 2"), "end", -1);

    // resize to two cells larger (+2 days) ; no delay
    awaitWriteDef = false;
    await resizePill(getPillWrapper("Task 2"), "end", +2);

    writeDef.resolve();
    await nextTick();

    assert.verifySteps([
        JSON.stringify(["get_views", []]),
        JSON.stringify(["get_gantt_data", []]),
        JSON.stringify(["write", [[2], { stop: "2018-12-21 06:29:59" }]]),
        JSON.stringify(["get_gantt_data", []]),
        JSON.stringify(["write", [[2], { stop: "2018-12-24 06:29:59" }]]),
        JSON.stringify(["get_gantt_data", []]),
    ]);
});

QUnit.test("concurrent pill resizes and open, dialog show updated number", async (assert) => {
    assert.expect(1);

    serverData.views["tasks,false,form"] = /* xml */ `
        <form>
            <field name="name"/>
            <field name="start"/>
            <field name="stop"/>
        </form>`;

    const def = makeDeferred();
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        domain: [["id", "=", 2]],
        async mockRPC(_route, { method }) {
            if (method === "write") {
                await def;
            }
        },
    });

    await resizePill(getPillWrapper("Task 2"), "end", +2);
    await editPill("Task 2");

    def.resolve();
    await nextTick();

    assert.strictEqual(
        document.querySelector(".modal [name=stop] input").value,
        "12/24/2018 07:29:59"
    );
});

// OTHER TESTS

QUnit.test("DST spring forward", async (assert) => {
    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [
        {
            id: 1,
            name: "DST Task 1",
            start: `${DST_DATES.winterToSummer.before} 03:00:00`,
            stop: `${DST_DATES.winterToSummer.before} 03:30:00`,
        },
        {
            id: 2,
            name: "DST Task 2",
            start: `${DST_DATES.winterToSummer.after} 03:00:00`,
            stop: `${DST_DATES.winterToSummer.after} 03:30:00`,
        },
    ];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="day"/>',
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });

    let content = getGridContent();
    assert.deepEqual(content.columnHeaders.slice(0, 4), ["12am", "1am", "2am", "3am"]);
    assert.deepEqual(content.rows[0].pills, [
        {
            colSpan: "4am -> 4am",
            level: 0,
            title: "DST Task 1",
        },
    ]);

    await click(target, SELECTORS.nextButton);

    content = getGridContent();
    assert.deepEqual(content.columnHeaders.slice(0, 4), ["12am", "1am", "3am", "4am"]);
    assert.deepEqual(content.rows[0].pills, [
        {
            colSpan: "5am -> 5am",
            level: 0,
            title: "DST Task 2",
        },
    ]);
});

QUnit.test("DST fall back", async (assert) => {
    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [
        {
            id: 1,
            name: "DST Task 1",
            start: `${DST_DATES.summerToWinter.before} 03:00:00`,
            stop: `${DST_DATES.summerToWinter.before} 03:30:00`,
        },
        {
            id: 2,
            name: "DST Task 2",
            start: `${DST_DATES.summerToWinter.after} 03:00:00`,
            stop: `${DST_DATES.summerToWinter.after} 03:30:00`,
        },
    ];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="day"/>',
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    let content = getGridContent();
    assert.deepEqual(content.columnHeaders.slice(0, 4), ["12am", "1am", "2am", "3am"]);
    assert.deepEqual(content.rows[0].pills, [
        {
            colSpan: "5am -> 5am",
            level: 0,
            title: "DST Task 1",
        },
    ]);

    await click(target, SELECTORS.nextButton);

    content = getGridContent();
    assert.deepEqual(content.columnHeaders.slice(0, 4), ["12am", "1am", "2am", "2am"]);
    assert.deepEqual(content.rows[0].pills, [
        {
            colSpan: "4am -> 4am",
            level: 0,
            title: "DST Task 2",
        },
    ]);
});

QUnit.test("Records spanning across DST should be displayed normally", async (assert) => {
    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [
        {
            id: 1,
            name: "DST Task 1",
            start: `${DST_DATES.winterToSummer.before} 03:00:00`,
            stop: `${DST_DATES.winterToSummer.after} 03:30:00`,
        },
        {
            id: 2,
            name: "DST Task 2",
            start: `${DST_DATES.summerToWinter.before} 03:00:00`,
            stop: `${DST_DATES.summerToWinter.after} 03:30:00`,
        },
    ];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" default_scale="year"/>',
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    assert.deepEqual(getGridContent().rows, [
        {
            pills: [
                { title: "DST Task 1", colSpan: "March -> March", level: 0 },
                { title: "DST Task 2", colSpan: "October -> October", level: 0 },
            ],
        },
    ]);
});

QUnit.test("delete attribute on dialog", async (assert) => {
    serverData.views = {
        "tasks,false,form": `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
                <field name="stage"/>
                <field name="project_id"/>
                <field name="user_id"/>
            </form>
        `,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" delete="0"/>',
    });

    await editPill("Task 1");

    assert.containsOnce(target, ".modal", "Should have opened a new dialog");
    assert.containsNone(
        target,
        ".o_form_button_remove",
        'should not have the "Remove" Button form dialog'
    );
});

QUnit.test(
    "move a pill in multi-level grop row after collapse and expand grouped row",
    async (assert) => {
        assert.expect(5);

        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: '<gantt date_start="start" date_stop="stop" />',
            groupBy: ["project_id", "stage"],
            async mockRPC(_route, { args, method }) {
                if (method === "write") {
                    assert.deepEqual(args, [
                        [7],
                        {
                            project_id: 1,
                            start: "2018-12-02 12:30:12",
                            stop: "2018-12-02 18:29:59",
                        },
                    ]);
                }
            },
            domain: [["id", "in", [1, 7]]],
        });

        assert.strictEqual(getGridContent().rows.length, 4);

        // collapse the first group
        await click(target, `${SELECTORS.rowHeader}${SELECTORS.group}:nth-child(1)`);

        assert.doesNotHaveClass(
            target.querySelector(`${SELECTORS.rowHeader}:nth-child(1)`),
            "o_group_open",
            "'Project 1' group should be collapsed"
        );
        // expand the first group
        await click(target, `${SELECTORS.rowHeader}${SELECTORS.group}:nth-child(1)`);

        assert.hasClass(
            target.querySelector(`${SELECTORS.rowHeader}:nth-child(1)`),
            "o_group_open",
            "'Project 1' group should be expanded"
        );

        // move a pill (task 7) in the other row and in the day 2
        const { drop } = await dragPill("Task 7");
        await drop({ row: 1, column: 2, part: 2 });

        assert.strictEqual(getGridContent().rows.filter((x) => x.isGroup).length, 1);
    }
);

QUnit.test("plan dialog initial domain has the action domain as its only base", async (assert) => {
    assert.expect(14);

    serverData.views = {
        "tasks,false,gantt": `<gantt date_start="start" date_stop="stop"/>`,
        "tasks,false,list": `<tree><field name="name"/></tree>`,
        "tasks,false,search": `
                <search>
                    <filter name="project_one" string="Project 1" domain="[('project_id', '=', 1)]"/>
                </search>
            `,
    };
    const webClient = await createWebClient({
        serverData,
        mockRPC: function (route, args) {
            if (["get_gantt_data", "web_search_read"].includes(args.method)) {
                assert.step(args.kwargs.domain.toString());
            }
        },
    });

    const ganttAction = {
        name: "Tasks Gantt",
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [[false, "gantt"]],
    };

    // Load action without domain and open plan dialog
    await doAction(webClient, ganttAction);
    assert.verifySteps(["&,start,<=,2018-12-31 22:59:59,stop,>=,2018-11-30 23:00:00"]);
    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    assert.verifySteps(["|,start,=,false,stop,=,false"]);

    // Load action WITH domain and open plan dialog
    await doAction(webClient, {
        ...ganttAction,
        domain: [["project_id", "=", 1]],
    });
    assert.verifySteps([
        "&,project_id,=,1,&,start,<=,2018-12-31 22:59:59,stop,>=,2018-11-30 23:00:00",
    ]);

    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    assert.verifySteps(["&,project_id,=,1,|,start,=,false,stop,=,false"]);

    // Load action without domain, activate a filter and then open plan dialog
    await doAction(webClient, ganttAction);
    assert.verifySteps(["&,start,<=,2018-12-31 22:59:59,stop,>=,2018-11-30 23:00:00"]);

    await toggleSearchBarMenu(target);
    await toggleMenuItem(target, "Project 1");
    assert.verifySteps([
        "&,project_id,=,1,&,start,<=,2018-12-31 22:59:59,stop,>=,2018-11-30 23:00:00",
    ]);

    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    assert.verifySteps(["|,start,=,false,stop,=,false"]);
});

QUnit.test("No progress bar when no option set.", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop"
                    default_scale="week" scales="week"/>`,
        mockRPC(_, { method }) {
            if (method === "gantt_progress_bar") {
                throw new Error("Method should not be called");
            }
        },
    });
    assert.containsNone(target, SELECTORS.progressBar);
});

QUnit.test("Progress bar rpc is triggered when option set.", async (assert) => {
    assert.expect(13);
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="week" scales="week"
                default_group_by="user_id"
                progress_bar="user_id"
            >
                <field name="user_id"/>
            </gantt>
        `,
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 50, max_value: 100 },
                        2: { value: 25, max_value: 200 },
                    },
                };
            }
        },
    });
    assert.containsN(target, SELECTORS.progressBar, 2);
    const [progressBar1, progressBar2] = target.querySelectorAll(SELECTORS.progressBar);
    assert.hasClass(progressBar1, "o_gantt_group_success");
    assert.hasClass(progressBar2, "o_gantt_group_success");
    const [rowHeader1, rowHeader2] = [progressBar1.parentElement, progressBar2.parentElement];
    assert.ok(rowHeader1.matches(SELECTORS.rowHeader));
    assert.ok(rowHeader2.matches(SELECTORS.rowHeader));
    assert.doesNotHaveClass(rowHeader1, CLASSES.group);
    assert.doesNotHaveClass(rowHeader2, CLASSES.group);
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarBackground)].map((el) => el.style.width),
        ["50%", "12.5%"]
    );
    await hoverGridCell(1, 1);
    assert.deepEqual(target.querySelector(SELECTORS.progressBarForeground).textContent, "50h / 100h");
    await hoverGridCell(2, 1);
    assert.deepEqual(target.querySelector(SELECTORS.progressBarForeground).textContent, "25h / 200h");
});

QUnit.test("Progress bar when multilevel grouped.", async (assert) => {
    assert.expect(13);
    // Here the view is grouped twice on the same field.
    // This is not a common use case, but it is possible to achieve it
    // bu saving a default favorite with a groupby then apply it twice
    // on the same field through the groupby menu.
    // In this case, the progress bar should be displayed only once,
    // on the first level of grouping.
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="week" scales="week"
                default_group_by="user_id,user_id"
                progress_bar="user_id"
            >
                <field name="user_id"/>
            </gantt>
        `,
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 50, max_value: 100 },
                        2: { value: 25, max_value: 200 },
                    },
                };
            }
        },
    });
    assert.containsN(target, SELECTORS.progressBar, 2);
    const [progressBar1, progressBar2] = target.querySelectorAll(SELECTORS.progressBar);
    assert.hasClass(progressBar1, "o_gantt_group_success");
    assert.hasClass(progressBar2, "o_gantt_group_success");
    const [rowHeader1, rowHeader2] = [progressBar1.parentElement, progressBar2.parentElement];
    assert.ok(rowHeader1.matches(SELECTORS.rowHeader));
    assert.ok(rowHeader2.matches(SELECTORS.rowHeader));
    assert.hasClass(rowHeader1, CLASSES.group);
    assert.hasClass(rowHeader2, CLASSES.group);
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarBackground)].map((el) => el.style.width),
        ["50%", "12.5%"]
    );
    await hoverGridCell(1, 1);
    assert.deepEqual(target.querySelector(SELECTORS.progressBarForeground).textContent, "50h / 100h");
    await hoverGridCell(3, 1);
    assert.deepEqual(target.querySelector(SELECTORS.progressBarForeground).textContent, "25h / 200h");
});

QUnit.test("Progress bar warning when max_value is zero", async (assert) => {
    assert.expect(6);
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="week" scales="week"
                default_group_by="user_id"
                progress_bar="user_id"
            >
                <field name="user_id"/>
            </gantt>
        `,
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 50, max_value: 0 },
                        warning: "plop",
                    },
                };
            }
        },
    });
    assert.containsNone(target, SELECTORS.progressBarWarning);
    await hoverGridCell(1, 1);
    assert.containsOnce(target, SELECTORS.progressBarWarning);
    assert.strictEqual(
        target.querySelector(SELECTORS.progressBarWarning).parentElement.title,
        "plop 50h."
    );
});

QUnit.test("Progress bar when value less than hour", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop"
                    default_scale="week" scales="week"
                    default_group_by="user_id"
                    progress_bar="user_id">
                    <field name="user_id"/>
                </gantt>`,
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 0.50, max_value: 100 },
                    },
                };
            }
        },
    });
    assert.containsOnce(target, SELECTORS.progressBar);
    await hoverGridCell(1, 1);
    assert.deepEqual(
        target.querySelector(SELECTORS.progressBarForeground).textContent,
        "0h30 / 100h"
    );
});

QUnit.test("Progress bar danger when ratio > 100", async (assert) => {
    assert.expect(8);
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop"
                    default_scale="week" scales="week"
                    default_group_by="user_id"
                    progress_bar="user_id">
                    <field name="user_id"/>
                </gantt>`,
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [1, 2] });
                return {
                    user_id: {
                        1: { value: 150, max_value: 100 },
                    },
                };
            }
        },
    });
    assert.containsOnce(target, SELECTORS.progressBar);
    assert.strictEqual(target.querySelector(SELECTORS.progressBarBackground).style.width, "100%");
    assert.hasClass(target.querySelector(SELECTORS.progressBar), "o_gantt_group_danger");
    await hoverGridCell(1, 1);
    assert.hasClass(
        target.querySelector(SELECTORS.progressBarForeground).parentElement,
        "text-bg-danger"
    );
    assert.deepEqual(
        target.querySelector(SELECTORS.progressBarForeground).textContent,
        "150h / 100h"
    );
});

QUnit.test("Falsy search field will return an empty rows", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="week" scales="week"
                progress_bar="user_id"
            >
                <field name="user_id"/>
            </gantt>
        `,
        groupBy: ["project_id", "user_id"],
        domain: [["id", "=", 5]],
    });
    assert.containsOnce(target, ".o_gantt_row_sidebar_empty");
    assert.containsNone(target, SELECTORS.progressBar);
});

QUnit.test("Search field return rows with progressbar", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="week" scales="week"
                progress_bar="user_id"
            >
                <field name="user_id"/>
            </gantt>
        `,
        groupBy: ["project_id", "user_id"],
        domain: [["id", "=", 2]],
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "tasks");
                assert.deepEqual(args[0], ["user_id"]);
                assert.deepEqual(args[1], { user_id: [2] });
                return {
                    user_id: {
                        2: { value: 25, max_value: 200 },
                    },
                };
            }
        },
    });
    const { rows } = getGridContent();
    assert.deepEqual(
        rows.map((r) => r.title),
        ["Project 1", "User 2"]
    );
    assert.containsOnce(target, SELECTORS.progressBar);
    assert.strictEqual(target.querySelector(SELECTORS.progressBarBackground).style.width, "12.5%");
});

QUnit.test("add record in empty gantt", async (assert) => {
    serverData.models.tasks.records = [];
    serverData.models.tasks.fields.stage_id.domain = "[('id', '!=', False)]";
    serverData.views = {
        "tasks,false,form": `
            <form>
                <field name="stage_id" widget="statusbar"/>
                <field name="project_id"/>
                <field name="start"/>
                <field name="stop"/>
            </form>
        `,
    };
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" plan="false"/>',
        groupBy: ["project_id"],
    });
    await hoverGridCell(1, 10);
    await clickCell(1, 10);
    assert.containsOnce(target, ".modal");
});

QUnit.test(
    "Only the task name appears in the pill title when the pill_label option is not set",
    async (assert) => {
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: `<gantt date_start="start" date_stop="stop"
                    default_scale="week" scales="week"/>`,
        });
        assert.deepEqual(getTexts(SELECTORS.pill), [
            "Task 1", // the pill should not include DateTime in the title
            "Task 2",
            "Task 4",
            "Task 7",
        ]);
    }
);

QUnit.test(
    "The date and task name appears in the pill title when the pill_label option is set",
    async (assert) => {
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: `<gantt date_start="start" date_stop="stop"
                    default_scale="week" scales="week"
                    pill_label="True"/>`,
        });
        assert.deepEqual(getTexts(SELECTORS.pill), [
            "11/30 - 12/31 - Task 1", // the task span across in week then DateTime should be displayed on the pill label
            "Task 2", // the task does not span across in week scale then DateTime shouldn't be displayed on the pill label
            "Task 4",
            "Task 7",
        ]);
    }
);

QUnit.test("A task should always have a title (pill_label='1', scale 'week')", async (assert) => {
    serverData.models.tasks.fields.allocated_hours = { type: "float", string: "Allocated Hours" };
    serverData.models.tasks.records = [
        {
            id: 1,
            name: "Task 1",
            start: "2018-12-17 08:30:00",
            stop: "2018-12-17 19:30:00", // span only one day
            allocated_hours: 0,
        },
        {
            id: 2,
            name: "Task 2",
            start: "2018-12-18 08:30:00",
            stop: "2018-12-18 19:30:00", // span only one day
            allocated_hours: 6,
        },
        {
            id: 3,
            name: "Task 3",
            start: "2018-12-18 08:30:00",
            stop: "2018-12-19 19:30:00", // span two days
            allocated_hours: 6,
        },
        {
            id: 4,
            name: "Task 4",
            start: "2018-12-08 08:30:00",
            stop: "2019-02-18 19:30:00", // span two weeks
            allocated_hours: 6,
        },
        {
            id: 5,
            name: "Task 5",
            start: "2018-12-18 08:30:00",
            stop: "2019-02-18 19:30:00", // span two months
            allocated_hours: 6,
        },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt date_start="start" date_stop="stop" pill_label="True" default_scale="week">
                <field name="allocated_hours"/>
            </gantt>
        `,
    });
    const titleMapping = [
        { name: "Task 4", title: "12/8-2/18-Task4" },
        { name: "Task 1", title: "Task1" },
        { name: "Task 2", title: "9:30AM-8:30PM(6h)-Task2" },
        { name: "Task 3", title: "Task3" },
        { name: "Task 5", title: "12/18-2/18-Task5" },
    ];

    assert.deepEqual(
        getTexts(".o_gantt_pill").map((t) => t.replace(/\s*/g, "")),
        titleMapping.map((e) => e.title)
    );

    const pills = target.querySelectorAll(".o_gantt_pill");
    for (let i = 0; i < pills.length; i++) {
        await click(pills[i]);
        assert.strictEqual(getText(".o_popover .popover-header"), titleMapping[i].name);
    }
});

QUnit.test("A task should always have a title (pill_label='1', scale 'month')", async (assert) => {
    serverData.models.tasks.fields.allocated_hours = { type: "float", string: "Allocated Hours" };
    serverData.models.tasks.records = [
        {
            id: 1,
            name: "Task 1",
            start: "2018-12-15 08:30:00",
            stop: "2018-12-15 19:30:00", // span only one day
            allocated_hours: 0,
        },
        {
            id: 2,
            name: "Task 2",
            start: "2018-12-16 08:30:00",
            stop: "2018-12-16 19:30:00", // span only one day
            allocated_hours: 6,
        },
        {
            id: 3,
            name: "Task 3",
            start: "2018-12-16 08:30:00",
            stop: "2018-12-17 18:30:00", // span two days
            allocated_hours: 6,
        },
        {
            id: 4,
            name: "Task 4",
            start: "2018-12-16 08:30:00",
            stop: "2019-02-18 19:30:00", // span two months
            allocated_hours: 6,
        },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt date_start="start" date_stop="stop" pill_label="True">
                <field name="allocated_hours"/>
            </gantt>
        `,
    });

    const titleMapping = [
        { name: "Task 1", title: "Task1" },
        { name: "Task 2", title: "9:30AM-8:30PM(6h)" },
        { name: "Task 3", title: "Task3" },
        { name: "Task 4", title: "12/16-2/18-Task4" },
    ];

    assert.deepEqual(
        getTexts(".o_gantt_pill").map((t) => t.replace(/\s*/g, "")),
        titleMapping.map((e) => e.title)
    );

    const pills = target.querySelectorAll(".o_gantt_pill");
    for (let i = 0; i < pills.length; i++) {
        await click(pills[i]);
        assert.strictEqual(getText(".o_popover .popover-header"), titleMapping[i].name);
    }
});

QUnit.test("position of no content help in sample mode", async (assert) => {
    patchWithCleanup(GanttController.prototype, {
        setup() {
            super.setup(...arguments);
            const rootRef = useRef("root");
            useEffect(() => {
                rootRef.el.querySelector(".o_content.o_view_sample_data").style.position =
                    "relative";
            });
        },
    });

    patchWithCleanup(GanttRenderer.prototype, {
        isDisabled(row) {
            if (this.visibleRows.indexOf(row) === 0) {
                return false;
            }
            return true;
        },
    });
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `<gantt date_start="start" date_stop="stop" sample="1"/>`,
        groupBy: ["user_id"],
        domain: Domain.FALSE.toList(),
    });
    assert.containsOnce(target, ".o_view_nocontent");
    assert.doesNotHaveClass(target.querySelector(".o_gantt_row_header"), "o_sample_data_disabled");
    const noContentHelp = target.querySelector(".o_view_nocontent");
    const noContentHelpTop = noContentHelp.getBoundingClientRect().top;
    const firstRowHeader = target.querySelector(".o_gantt_row_header");
    const firstRowHeaderBottom = firstRowHeader.getBoundingClientRect().bottom;
    assert.ok(noContentHelpTop - firstRowHeaderBottom < 3);
});

QUnit.test(
    "gantt view grouped by a boolean field: row titles should be 'True' or 'False'",
    async (assert) => {
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: `<gantt date_start="start" date_stop="stop"/>`,
            groupBy: ["exclude"],
        });
        assert.deepEqual(
            getGridContent().rows.map((r) => r.title),
            ["False", "True"]
        );
    }
);

QUnit.test("date grid and dst winterToSummer (1 cell part)", async (assert) => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="day"
                precision="{'day':'hour:full', 'week':'day:full', 'month':'day:full', 'year':'month:full' }"
            />
        `,
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.dateGridColumns.map((d) => d.toString());
    }

    assert.deepEqual(getGridInfo(), [
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-30T01:00:00.000+01:00",
        "2019-03-30T02:00:00.000+01:00",
        "2019-03-30T03:00:00.000+01:00",
        "2019-03-30T04:00:00.000+01:00",
        "2019-03-30T05:00:00.000+01:00",
        "2019-03-30T06:00:00.000+01:00",
        "2019-03-30T07:00:00.000+01:00",
        "2019-03-30T08:00:00.000+01:00",
        "2019-03-30T09:00:00.000+01:00",
        "2019-03-30T10:00:00.000+01:00",
        "2019-03-30T11:00:00.000+01:00",
        "2019-03-30T12:00:00.000+01:00",
        "2019-03-30T13:00:00.000+01:00",
        "2019-03-30T14:00:00.000+01:00",
        "2019-03-30T15:00:00.000+01:00",
        "2019-03-30T16:00:00.000+01:00",
        "2019-03-30T17:00:00.000+01:00",
        "2019-03-30T18:00:00.000+01:00",
        "2019-03-30T19:00:00.000+01:00",
        "2019-03-30T20:00:00.000+01:00",
        "2019-03-30T21:00:00.000+01:00",
        "2019-03-30T22:00:00.000+01:00",
        "2019-03-30T23:00:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
    ]);

    await click(target, SELECTORS.nextButton);

    assert.deepEqual(getGridInfo(), [
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T01:00:00.000+01:00",
        "2019-03-31T03:00:00.000+02:00",
        "2019-03-31T04:00:00.000+02:00",
        "2019-03-31T05:00:00.000+02:00",
        "2019-03-31T06:00:00.000+02:00",
        "2019-03-31T07:00:00.000+02:00",
        "2019-03-31T08:00:00.000+02:00",
        "2019-03-31T09:00:00.000+02:00",
        "2019-03-31T10:00:00.000+02:00",
        "2019-03-31T11:00:00.000+02:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-03-31T13:00:00.000+02:00",
        "2019-03-31T14:00:00.000+02:00",
        "2019-03-31T15:00:00.000+02:00",
        "2019-03-31T16:00:00.000+02:00",
        "2019-03-31T17:00:00.000+02:00",
        "2019-03-31T18:00:00.000+02:00",
        "2019-03-31T19:00:00.000+02:00",
        "2019-03-31T20:00:00.000+02:00",
        "2019-03-31T21:00:00.000+02:00",
        "2019-03-31T22:00:00.000+02:00",
        "2019-03-31T23:00:00.000+02:00",
        "2019-04-01T00:00:00.000+02:00",
    ]);

    await setScale("week");

    assert.deepEqual(getGridInfo(), [
        "2019-03-31T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-04-02T00:00:00.000+02:00",
        "2019-04-03T00:00:00.000+02:00",
        "2019-04-04T00:00:00.000+02:00",
        "2019-04-05T00:00:00.000+02:00",
        "2019-04-06T00:00:00.000+02:00",
        "2019-04-07T00:00:00.000+02:00",
    ]);

    await setScale("month");

    assert.deepEqual(getGridInfo(), [
        "2019-03-01T00:00:00.000+01:00",
        "2019-03-02T00:00:00.000+01:00",
        "2019-03-03T00:00:00.000+01:00",
        "2019-03-04T00:00:00.000+01:00",
        "2019-03-05T00:00:00.000+01:00",
        "2019-03-06T00:00:00.000+01:00",
        "2019-03-07T00:00:00.000+01:00",
        "2019-03-08T00:00:00.000+01:00",
        "2019-03-09T00:00:00.000+01:00",
        "2019-03-10T00:00:00.000+01:00",
        "2019-03-11T00:00:00.000+01:00",
        "2019-03-12T00:00:00.000+01:00",
        "2019-03-13T00:00:00.000+01:00",
        "2019-03-14T00:00:00.000+01:00",
        "2019-03-15T00:00:00.000+01:00",
        "2019-03-16T00:00:00.000+01:00",
        "2019-03-17T00:00:00.000+01:00",
        "2019-03-18T00:00:00.000+01:00",
        "2019-03-19T00:00:00.000+01:00",
        "2019-03-20T00:00:00.000+01:00",
        "2019-03-21T00:00:00.000+01:00",
        "2019-03-22T00:00:00.000+01:00",
        "2019-03-23T00:00:00.000+01:00",
        "2019-03-24T00:00:00.000+01:00",
        "2019-03-25T00:00:00.000+01:00",
        "2019-03-26T00:00:00.000+01:00",
        "2019-03-27T00:00:00.000+01:00",
        "2019-03-28T00:00:00.000+01:00",
        "2019-03-29T00:00:00.000+01:00",
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
    ]);

    await setScale("year");

    assert.deepEqual(getGridInfo(), [
        "2019-01-01T00:00:00.000+01:00",
        "2019-02-01T00:00:00.000+01:00",
        "2019-03-01T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-05-01T00:00:00.000+02:00",
        "2019-06-01T00:00:00.000+02:00",
        "2019-07-01T00:00:00.000+02:00",
        "2019-08-01T00:00:00.000+02:00",
        "2019-09-01T00:00:00.000+02:00",
        "2019-10-01T00:00:00.000+02:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-12-01T00:00:00.000+01:00",
        "2020-01-01T00:00:00.000+01:00",
    ]);
});

QUnit.test("date grid and dst summerToWinter (1 cell part)", async (assert) => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="day"
                precision="{'day':'hour:full', 'week':'day:full', 'month':'day:full', 'year':'month:full' }"
            />`,
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.dateGridColumns.map((d) => d.toString());
    }

    assert.deepEqual(getGridInfo(), [
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-26T01:00:00.000+02:00",
        "2019-10-26T02:00:00.000+02:00",
        "2019-10-26T03:00:00.000+02:00",
        "2019-10-26T04:00:00.000+02:00",
        "2019-10-26T05:00:00.000+02:00",
        "2019-10-26T06:00:00.000+02:00",
        "2019-10-26T07:00:00.000+02:00",
        "2019-10-26T08:00:00.000+02:00",
        "2019-10-26T09:00:00.000+02:00",
        "2019-10-26T10:00:00.000+02:00",
        "2019-10-26T11:00:00.000+02:00",
        "2019-10-26T12:00:00.000+02:00",
        "2019-10-26T13:00:00.000+02:00",
        "2019-10-26T14:00:00.000+02:00",
        "2019-10-26T15:00:00.000+02:00",
        "2019-10-26T16:00:00.000+02:00",
        "2019-10-26T17:00:00.000+02:00",
        "2019-10-26T18:00:00.000+02:00",
        "2019-10-26T19:00:00.000+02:00",
        "2019-10-26T20:00:00.000+02:00",
        "2019-10-26T21:00:00.000+02:00",
        "2019-10-26T22:00:00.000+02:00",
        "2019-10-26T23:00:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
    ]);

    await click(target, SELECTORS.nextButton);

    assert.deepEqual(getGridInfo(), [
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T01:00:00.000+02:00",
        "2019-10-27T02:00:00.000+02:00",
        "2019-10-27T02:00:00.000+01:00",
        "2019-10-27T03:00:00.000+01:00",
        "2019-10-27T04:00:00.000+01:00",
        "2019-10-27T05:00:00.000+01:00",
        "2019-10-27T06:00:00.000+01:00",
        "2019-10-27T07:00:00.000+01:00",
        "2019-10-27T08:00:00.000+01:00",
        "2019-10-27T09:00:00.000+01:00",
        "2019-10-27T10:00:00.000+01:00",
        "2019-10-27T11:00:00.000+01:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-27T13:00:00.000+01:00",
        "2019-10-27T14:00:00.000+01:00",
        "2019-10-27T15:00:00.000+01:00",
        "2019-10-27T16:00:00.000+01:00",
        "2019-10-27T17:00:00.000+01:00",
        "2019-10-27T18:00:00.000+01:00",
        "2019-10-27T19:00:00.000+01:00",
        "2019-10-27T20:00:00.000+01:00",
        "2019-10-27T21:00:00.000+01:00",
        "2019-10-27T22:00:00.000+01:00",
        "2019-10-27T23:00:00.000+01:00",
        "2019-10-28T00:00:00.000+01:00",
    ]);

    await setScale("week");

    assert.deepEqual(getGridInfo(), [
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-11-02T00:00:00.000+01:00",
        "2019-11-03T00:00:00.000+01:00",
    ]);

    await setScale("month");

    assert.deepEqual(getGridInfo(), [
        "2019-10-01T00:00:00.000+02:00",
        "2019-10-02T00:00:00.000+02:00",
        "2019-10-03T00:00:00.000+02:00",
        "2019-10-04T00:00:00.000+02:00",
        "2019-10-05T00:00:00.000+02:00",
        "2019-10-06T00:00:00.000+02:00",
        "2019-10-07T00:00:00.000+02:00",
        "2019-10-08T00:00:00.000+02:00",
        "2019-10-09T00:00:00.000+02:00",
        "2019-10-10T00:00:00.000+02:00",
        "2019-10-11T00:00:00.000+02:00",
        "2019-10-12T00:00:00.000+02:00",
        "2019-10-13T00:00:00.000+02:00",
        "2019-10-14T00:00:00.000+02:00",
        "2019-10-15T00:00:00.000+02:00",
        "2019-10-16T00:00:00.000+02:00",
        "2019-10-17T00:00:00.000+02:00",
        "2019-10-18T00:00:00.000+02:00",
        "2019-10-19T00:00:00.000+02:00",
        "2019-10-20T00:00:00.000+02:00",
        "2019-10-21T00:00:00.000+02:00",
        "2019-10-22T00:00:00.000+02:00",
        "2019-10-23T00:00:00.000+02:00",
        "2019-10-24T00:00:00.000+02:00",
        "2019-10-25T00:00:00.000+02:00",
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
    ]);

    await setScale("year");

    assert.deepEqual(getGridInfo(), [
        "2019-01-01T00:00:00.000+01:00",
        "2019-02-01T00:00:00.000+01:00",
        "2019-03-01T00:00:00.000+01:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-05-01T00:00:00.000+02:00",
        "2019-06-01T00:00:00.000+02:00",
        "2019-07-01T00:00:00.000+02:00",
        "2019-08-01T00:00:00.000+02:00",
        "2019-09-01T00:00:00.000+02:00",
        "2019-10-01T00:00:00.000+02:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-12-01T00:00:00.000+01:00",
        "2020-01-01T00:00:00.000+01:00",
    ]);
});

QUnit.test("date grid and dst winterToSummer (2 cell part)", async (assert) => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="day"
                precision="{'day':'hour:half', 'week':'day:half', 'month':'day:half'}"
            />
        `,
        domain: [["id", "=", 8]],
        context: {
            initialDate: `${DST_DATES.winterToSummer.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.dateGridColumns.map((d) => d.toString());
    }

    assert.deepEqual(getGridInfo(), [
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-30T00:30:00.000+01:00",
        "2019-03-30T01:00:00.000+01:00",
        "2019-03-30T01:30:00.000+01:00",
        "2019-03-30T02:00:00.000+01:00",
        "2019-03-30T02:30:00.000+01:00",
        "2019-03-30T03:00:00.000+01:00",
        "2019-03-30T03:30:00.000+01:00",
        "2019-03-30T04:00:00.000+01:00",
        "2019-03-30T04:30:00.000+01:00",
        "2019-03-30T05:00:00.000+01:00",
        "2019-03-30T05:30:00.000+01:00",
        "2019-03-30T06:00:00.000+01:00",
        "2019-03-30T06:30:00.000+01:00",
        "2019-03-30T07:00:00.000+01:00",
        "2019-03-30T07:30:00.000+01:00",
        "2019-03-30T08:00:00.000+01:00",
        "2019-03-30T08:30:00.000+01:00",
        "2019-03-30T09:00:00.000+01:00",
        "2019-03-30T09:30:00.000+01:00",
        "2019-03-30T10:00:00.000+01:00",
        "2019-03-30T10:30:00.000+01:00",
        "2019-03-30T11:00:00.000+01:00",
        "2019-03-30T11:30:00.000+01:00",
        "2019-03-30T12:00:00.000+01:00",
        "2019-03-30T12:30:00.000+01:00",
        "2019-03-30T13:00:00.000+01:00",
        "2019-03-30T13:30:00.000+01:00",
        "2019-03-30T14:00:00.000+01:00",
        "2019-03-30T14:30:00.000+01:00",
        "2019-03-30T15:00:00.000+01:00",
        "2019-03-30T15:30:00.000+01:00",
        "2019-03-30T16:00:00.000+01:00",
        "2019-03-30T16:30:00.000+01:00",
        "2019-03-30T17:00:00.000+01:00",
        "2019-03-30T17:30:00.000+01:00",
        "2019-03-30T18:00:00.000+01:00",
        "2019-03-30T18:30:00.000+01:00",
        "2019-03-30T19:00:00.000+01:00",
        "2019-03-30T19:30:00.000+01:00",
        "2019-03-30T20:00:00.000+01:00",
        "2019-03-30T20:30:00.000+01:00",
        "2019-03-30T21:00:00.000+01:00",
        "2019-03-30T21:30:00.000+01:00",
        "2019-03-30T22:00:00.000+01:00",
        "2019-03-30T22:30:00.000+01:00",
        "2019-03-30T23:00:00.000+01:00",
        "2019-03-30T23:30:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
    ]);

    await click(target, SELECTORS.nextButton);

    assert.deepEqual(getGridInfo(), [
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T00:30:00.000+01:00",
        "2019-03-31T01:00:00.000+01:00",
        "2019-03-31T01:30:00.000+01:00",
        "2019-03-31T03:00:00.000+02:00",
        "2019-03-31T03:30:00.000+02:00",
        "2019-03-31T04:00:00.000+02:00",
        "2019-03-31T04:30:00.000+02:00",
        "2019-03-31T05:00:00.000+02:00",
        "2019-03-31T05:30:00.000+02:00",
        "2019-03-31T06:00:00.000+02:00",
        "2019-03-31T06:30:00.000+02:00",
        "2019-03-31T07:00:00.000+02:00",
        "2019-03-31T07:30:00.000+02:00",
        "2019-03-31T08:00:00.000+02:00",
        "2019-03-31T08:30:00.000+02:00",
        "2019-03-31T09:00:00.000+02:00",
        "2019-03-31T09:30:00.000+02:00",
        "2019-03-31T10:00:00.000+02:00",
        "2019-03-31T10:30:00.000+02:00",
        "2019-03-31T11:00:00.000+02:00",
        "2019-03-31T11:30:00.000+02:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-03-31T12:30:00.000+02:00",
        "2019-03-31T13:00:00.000+02:00",
        "2019-03-31T13:30:00.000+02:00",
        "2019-03-31T14:00:00.000+02:00",
        "2019-03-31T14:30:00.000+02:00",
        "2019-03-31T15:00:00.000+02:00",
        "2019-03-31T15:30:00.000+02:00",
        "2019-03-31T16:00:00.000+02:00",
        "2019-03-31T16:30:00.000+02:00",
        "2019-03-31T17:00:00.000+02:00",
        "2019-03-31T17:30:00.000+02:00",
        "2019-03-31T18:00:00.000+02:00",
        "2019-03-31T18:30:00.000+02:00",
        "2019-03-31T19:00:00.000+02:00",
        "2019-03-31T19:30:00.000+02:00",
        "2019-03-31T20:00:00.000+02:00",
        "2019-03-31T20:30:00.000+02:00",
        "2019-03-31T21:00:00.000+02:00",
        "2019-03-31T21:30:00.000+02:00",
        "2019-03-31T22:00:00.000+02:00",
        "2019-03-31T22:30:00.000+02:00",
        "2019-03-31T23:00:00.000+02:00",
        "2019-03-31T23:30:00.000+02:00",
        "2019-04-01T00:00:00.000+02:00",
    ]);

    await setScale("week");

    assert.deepEqual(getGridInfo(), [
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-04-01T00:00:00.000+02:00",
        "2019-04-01T12:00:00.000+02:00",
        "2019-04-02T00:00:00.000+02:00",
        "2019-04-02T12:00:00.000+02:00",
        "2019-04-03T00:00:00.000+02:00",
        "2019-04-03T12:00:00.000+02:00",
        "2019-04-04T00:00:00.000+02:00",
        "2019-04-04T12:00:00.000+02:00",
        "2019-04-05T00:00:00.000+02:00",
        "2019-04-05T12:00:00.000+02:00",
        "2019-04-06T00:00:00.000+02:00",
        "2019-04-06T12:00:00.000+02:00",
        "2019-04-07T00:00:00.000+02:00",
    ]);

    await setScale("month");

    assert.deepEqual(getGridInfo(), [
        "2019-03-01T00:00:00.000+01:00",
        "2019-03-01T12:00:00.000+01:00",
        "2019-03-02T00:00:00.000+01:00",
        "2019-03-02T12:00:00.000+01:00",
        "2019-03-03T00:00:00.000+01:00",
        "2019-03-03T12:00:00.000+01:00",
        "2019-03-04T00:00:00.000+01:00",
        "2019-03-04T12:00:00.000+01:00",
        "2019-03-05T00:00:00.000+01:00",
        "2019-03-05T12:00:00.000+01:00",
        "2019-03-06T00:00:00.000+01:00",
        "2019-03-06T12:00:00.000+01:00",
        "2019-03-07T00:00:00.000+01:00",
        "2019-03-07T12:00:00.000+01:00",
        "2019-03-08T00:00:00.000+01:00",
        "2019-03-08T12:00:00.000+01:00",
        "2019-03-09T00:00:00.000+01:00",
        "2019-03-09T12:00:00.000+01:00",
        "2019-03-10T00:00:00.000+01:00",
        "2019-03-10T12:00:00.000+01:00",
        "2019-03-11T00:00:00.000+01:00",
        "2019-03-11T12:00:00.000+01:00",
        "2019-03-12T00:00:00.000+01:00",
        "2019-03-12T12:00:00.000+01:00",
        "2019-03-13T00:00:00.000+01:00",
        "2019-03-13T12:00:00.000+01:00",
        "2019-03-14T00:00:00.000+01:00",
        "2019-03-14T12:00:00.000+01:00",
        "2019-03-15T00:00:00.000+01:00",
        "2019-03-15T12:00:00.000+01:00",
        "2019-03-16T00:00:00.000+01:00",
        "2019-03-16T12:00:00.000+01:00",
        "2019-03-17T00:00:00.000+01:00",
        "2019-03-17T12:00:00.000+01:00",
        "2019-03-18T00:00:00.000+01:00",
        "2019-03-18T12:00:00.000+01:00",
        "2019-03-19T00:00:00.000+01:00",
        "2019-03-19T12:00:00.000+01:00",
        "2019-03-20T00:00:00.000+01:00",
        "2019-03-20T12:00:00.000+01:00",
        "2019-03-21T00:00:00.000+01:00",
        "2019-03-21T12:00:00.000+01:00",
        "2019-03-22T00:00:00.000+01:00",
        "2019-03-22T12:00:00.000+01:00",
        "2019-03-23T00:00:00.000+01:00",
        "2019-03-23T12:00:00.000+01:00",
        "2019-03-24T00:00:00.000+01:00",
        "2019-03-24T12:00:00.000+01:00",
        "2019-03-25T00:00:00.000+01:00",
        "2019-03-25T12:00:00.000+01:00",
        "2019-03-26T00:00:00.000+01:00",
        "2019-03-26T12:00:00.000+01:00",
        "2019-03-27T00:00:00.000+01:00",
        "2019-03-27T12:00:00.000+01:00",
        "2019-03-28T00:00:00.000+01:00",
        "2019-03-28T12:00:00.000+01:00",
        "2019-03-29T00:00:00.000+01:00",
        "2019-03-29T12:00:00.000+01:00",
        "2019-03-30T00:00:00.000+01:00",
        "2019-03-30T12:00:00.000+01:00",
        "2019-03-31T00:00:00.000+01:00",
        "2019-03-31T12:00:00.000+02:00",
        "2019-04-01T00:00:00.000+02:00",
    ]);
});

QUnit.test("date grid and dst summerToWinter (2 cell part)", async (assert) => {
    let renderer;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    patchWithCleanup(luxon.Settings, {
        defaultZone: luxon.IANAZone.create("Europe/Brussels"),
    });

    serverData.models.tasks.records = [];

    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                default_scale="day"
                precision="{'day':'hour:half', 'week':'day:half', 'month':'day:half'}"
            />
        `,
        context: {
            initialDate: `${DST_DATES.summerToWinter.before} 08:00:00`,
        },
    });

    function getGridInfo() {
        return renderer.dateGridColumns.map((d) => d.toString());
    }

    assert.deepEqual(getGridInfo(), [
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-26T00:30:00.000+02:00",
        "2019-10-26T01:00:00.000+02:00",
        "2019-10-26T01:30:00.000+02:00",
        "2019-10-26T02:00:00.000+02:00",
        "2019-10-26T02:30:00.000+02:00",
        "2019-10-26T03:00:00.000+02:00",
        "2019-10-26T03:30:00.000+02:00",
        "2019-10-26T04:00:00.000+02:00",
        "2019-10-26T04:30:00.000+02:00",
        "2019-10-26T05:00:00.000+02:00",
        "2019-10-26T05:30:00.000+02:00",
        "2019-10-26T06:00:00.000+02:00",
        "2019-10-26T06:30:00.000+02:00",
        "2019-10-26T07:00:00.000+02:00",
        "2019-10-26T07:30:00.000+02:00",
        "2019-10-26T08:00:00.000+02:00",
        "2019-10-26T08:30:00.000+02:00",
        "2019-10-26T09:00:00.000+02:00",
        "2019-10-26T09:30:00.000+02:00",
        "2019-10-26T10:00:00.000+02:00",
        "2019-10-26T10:30:00.000+02:00",
        "2019-10-26T11:00:00.000+02:00",
        "2019-10-26T11:30:00.000+02:00",
        "2019-10-26T12:00:00.000+02:00",
        "2019-10-26T12:30:00.000+02:00",
        "2019-10-26T13:00:00.000+02:00",
        "2019-10-26T13:30:00.000+02:00",
        "2019-10-26T14:00:00.000+02:00",
        "2019-10-26T14:30:00.000+02:00",
        "2019-10-26T15:00:00.000+02:00",
        "2019-10-26T15:30:00.000+02:00",
        "2019-10-26T16:00:00.000+02:00",
        "2019-10-26T16:30:00.000+02:00",
        "2019-10-26T17:00:00.000+02:00",
        "2019-10-26T17:30:00.000+02:00",
        "2019-10-26T18:00:00.000+02:00",
        "2019-10-26T18:30:00.000+02:00",
        "2019-10-26T19:00:00.000+02:00",
        "2019-10-26T19:30:00.000+02:00",
        "2019-10-26T20:00:00.000+02:00",
        "2019-10-26T20:30:00.000+02:00",
        "2019-10-26T21:00:00.000+02:00",
        "2019-10-26T21:30:00.000+02:00",
        "2019-10-26T22:00:00.000+02:00",
        "2019-10-26T22:30:00.000+02:00",
        "2019-10-26T23:00:00.000+02:00",
        "2019-10-26T23:30:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
    ]);

    await click(target, SELECTORS.nextButton);

    assert.deepEqual(getGridInfo(), [
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T00:30:00.000+02:00",
        "2019-10-27T01:00:00.000+02:00",
        "2019-10-27T01:30:00.000+02:00",
        "2019-10-27T02:00:00.000+02:00",
        "2019-10-27T02:30:00.000+02:00",
        "2019-10-27T02:00:00.000+01:00",
        "2019-10-27T02:30:00.000+01:00",
        "2019-10-27T03:00:00.000+01:00",
        "2019-10-27T03:30:00.000+01:00",
        "2019-10-27T04:00:00.000+01:00",
        "2019-10-27T04:30:00.000+01:00",
        "2019-10-27T05:00:00.000+01:00",
        "2019-10-27T05:30:00.000+01:00",
        "2019-10-27T06:00:00.000+01:00",
        "2019-10-27T06:30:00.000+01:00",
        "2019-10-27T07:00:00.000+01:00",
        "2019-10-27T07:30:00.000+01:00",
        "2019-10-27T08:00:00.000+01:00",
        "2019-10-27T08:30:00.000+01:00",
        "2019-10-27T09:00:00.000+01:00",
        "2019-10-27T09:30:00.000+01:00",
        "2019-10-27T10:00:00.000+01:00",
        "2019-10-27T10:30:00.000+01:00",
        "2019-10-27T11:00:00.000+01:00",
        "2019-10-27T11:30:00.000+01:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-27T12:30:00.000+01:00",
        "2019-10-27T13:00:00.000+01:00",
        "2019-10-27T13:30:00.000+01:00",
        "2019-10-27T14:00:00.000+01:00",
        "2019-10-27T14:30:00.000+01:00",
        "2019-10-27T15:00:00.000+01:00",
        "2019-10-27T15:30:00.000+01:00",
        "2019-10-27T16:00:00.000+01:00",
        "2019-10-27T16:30:00.000+01:00",
        "2019-10-27T17:00:00.000+01:00",
        "2019-10-27T17:30:00.000+01:00",
        "2019-10-27T18:00:00.000+01:00",
        "2019-10-27T18:30:00.000+01:00",
        "2019-10-27T19:00:00.000+01:00",
        "2019-10-27T19:30:00.000+01:00",
        "2019-10-27T20:00:00.000+01:00",
        "2019-10-27T20:30:00.000+01:00",
        "2019-10-27T21:00:00.000+01:00",
        "2019-10-27T21:30:00.000+01:00",
        "2019-10-27T22:00:00.000+01:00",
        "2019-10-27T22:30:00.000+01:00",
        "2019-10-27T23:00:00.000+01:00",
        "2019-10-27T23:30:00.000+01:00",
        "2019-10-28T00:00:00.000+01:00",
    ]);

    await setScale("week");

    assert.deepEqual(getGridInfo(), [
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-28T12:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-29T12:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-30T12:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-10-31T12:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
        "2019-11-01T12:00:00.000+01:00",
        "2019-11-02T00:00:00.000+01:00",
        "2019-11-02T12:00:00.000+01:00",
        "2019-11-03T00:00:00.000+01:00",
    ]);

    await setScale("month");

    assert.deepEqual(getGridInfo(), [
        "2019-10-01T00:00:00.000+02:00",
        "2019-10-01T12:00:00.000+02:00",
        "2019-10-02T00:00:00.000+02:00",
        "2019-10-02T12:00:00.000+02:00",
        "2019-10-03T00:00:00.000+02:00",
        "2019-10-03T12:00:00.000+02:00",
        "2019-10-04T00:00:00.000+02:00",
        "2019-10-04T12:00:00.000+02:00",
        "2019-10-05T00:00:00.000+02:00",
        "2019-10-05T12:00:00.000+02:00",
        "2019-10-06T00:00:00.000+02:00",
        "2019-10-06T12:00:00.000+02:00",
        "2019-10-07T00:00:00.000+02:00",
        "2019-10-07T12:00:00.000+02:00",
        "2019-10-08T00:00:00.000+02:00",
        "2019-10-08T12:00:00.000+02:00",
        "2019-10-09T00:00:00.000+02:00",
        "2019-10-09T12:00:00.000+02:00",
        "2019-10-10T00:00:00.000+02:00",
        "2019-10-10T12:00:00.000+02:00",
        "2019-10-11T00:00:00.000+02:00",
        "2019-10-11T12:00:00.000+02:00",
        "2019-10-12T00:00:00.000+02:00",
        "2019-10-12T12:00:00.000+02:00",
        "2019-10-13T00:00:00.000+02:00",
        "2019-10-13T12:00:00.000+02:00",
        "2019-10-14T00:00:00.000+02:00",
        "2019-10-14T12:00:00.000+02:00",
        "2019-10-15T00:00:00.000+02:00",
        "2019-10-15T12:00:00.000+02:00",
        "2019-10-16T00:00:00.000+02:00",
        "2019-10-16T12:00:00.000+02:00",
        "2019-10-17T00:00:00.000+02:00",
        "2019-10-17T12:00:00.000+02:00",
        "2019-10-18T00:00:00.000+02:00",
        "2019-10-18T12:00:00.000+02:00",
        "2019-10-19T00:00:00.000+02:00",
        "2019-10-19T12:00:00.000+02:00",
        "2019-10-20T00:00:00.000+02:00",
        "2019-10-20T12:00:00.000+02:00",
        "2019-10-21T00:00:00.000+02:00",
        "2019-10-21T12:00:00.000+02:00",
        "2019-10-22T00:00:00.000+02:00",
        "2019-10-22T12:00:00.000+02:00",
        "2019-10-23T00:00:00.000+02:00",
        "2019-10-23T12:00:00.000+02:00",
        "2019-10-24T00:00:00.000+02:00",
        "2019-10-24T12:00:00.000+02:00",
        "2019-10-25T00:00:00.000+02:00",
        "2019-10-25T12:00:00.000+02:00",
        "2019-10-26T00:00:00.000+02:00",
        "2019-10-26T12:00:00.000+02:00",
        "2019-10-27T00:00:00.000+02:00",
        "2019-10-27T12:00:00.000+01:00",
        "2019-10-28T00:00:00.000+01:00",
        "2019-10-28T12:00:00.000+01:00",
        "2019-10-29T00:00:00.000+01:00",
        "2019-10-29T12:00:00.000+01:00",
        "2019-10-30T00:00:00.000+01:00",
        "2019-10-30T12:00:00.000+01:00",
        "2019-10-31T00:00:00.000+01:00",
        "2019-10-31T12:00:00.000+01:00",
        "2019-11-01T00:00:00.000+01:00",
    ]);
});

QUnit.test("groups_limit attribute (no groupBy)", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                groups_limit="2"
            />
        `,
        mockRPC(_, { method, kwargs }) {
            assert.step(method);
            if (kwargs.limit) {
                assert.step(`with limit ${kwargs.limit}`);
            }
        },
    });

    assert.containsNone(target, ".o_gantt_view .o_control_panel .o_pager"); // only one group here!
    assert.verifySteps(["get_views", "get_gantt_data", "with limit 2"]);
    const { rows } = getGridContent();
    assert.deepEqual(rows, [
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
                {
                    colSpan: "01 -> 31",
                    level: 1,
                    title: "Task 1",
                },
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
                {
                    colSpan: "20 -> 20 (1/2)",
                    level: 2,
                    title: "Task 4",
                },
                {
                    colSpan: "20 (1/2) -> 20",
                    level: 2,
                    title: "Task 7",
                },
                {
                    colSpan: "27 -> 31",
                    level: 0,
                    title: "Task 3",
                },
            ],
        },
    ]);
});

QUnit.test("groups_limit attribute (one groupBy)", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                groups_limit="2"
            />
        `,
        groupBy: ["stage_id"],
        mockRPC(_, { method, kwargs }) {
            assert.step(method);
            if (kwargs.limit) {
                assert.step(`with limit ${kwargs.limit}`);
                assert.step(`with offset ${kwargs.offset}`);
            }
        },
    });

    assert.containsOnce(target, ".o_gantt_view .o_control_panel .o_pager");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
    let rows = getGridContent().rows;
    assert.deepEqual(rows, [
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
            ],
            title: "todo",
        },
        {
            pills: [
                {
                    colSpan: "01 -> 31",
                    level: 0,
                    title: "Task 1",
                },
                {
                    colSpan: "20 (1/2) -> 20",
                    level: 1,
                    title: "Task 7",
                },
            ],
            title: "in_progress",
        },
    ]);
    assert.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);

    await click(target, ".o_pager_next");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "3-4");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
    rows = getGridContent().rows;
    assert.deepEqual(rows, [
        {
            pills: [
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "done",
        },
        {
            pills: [
                {
                    colSpan: "20 -> 20 (1/2)",
                    level: 0,
                    title: "Task 4",
                },
                {
                    colSpan: "27 -> 31",
                    level: 0,
                    title: "Task 3",
                },
            ],
            title: "cancel",
        },
    ]);
    assert.verifySteps(["get_gantt_data", "with limit 2", "with offset 2"]);
});

QUnit.test("groups_limit attribute (two groupBys)", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                groups_limit="2"
            />
        `,
        groupBy: ["stage_id", "project_id"],
        mockRPC(_, { method, kwargs }) {
            assert.step(method);
            if (kwargs.limit) {
                assert.step(`with limit ${kwargs.limit}`);
                assert.step(`with offset ${kwargs.offset}`);
            }
        },
    });

    assert.containsOnce(target, ".o_gantt_view .o_control_panel .o_pager");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5");
    let rows = getGridContent().rows;
    assert.deepEqual(rows, [
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    title: "1",
                },
            ],
            title: "todo",
        },
        {
            pills: [
                {
                    colSpan: "01 -> 04 (1/2)",
                    level: 0,
                    title: "Task 5",
                },
            ],
            title: "Project 2",
        },
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "01 -> 31",
                    title: "1",
                },
            ],
            title: "in_progress",
        },
        {
            pills: [
                {
                    colSpan: "01 -> 31",
                    level: 0,
                    title: "Task 1",
                },
            ],
            title: "Project 1",
        },
    ]);
    assert.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);

    await click(target, ".o_pager_next");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "3-4");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5");
    rows = getGridContent().rows;
    assert.deepEqual(rows, [
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "20 (1/2) -> 20",
                    title: "1",
                },
            ],
            title: "in_progress",
        },
        {
            pills: [
                {
                    colSpan: "20 (1/2) -> 20",
                    level: 0,
                    title: "Task 7",
                },
            ],
            title: "Project 2",
        },
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    title: "1",
                },
            ],
            title: "done",
        },
        {
            pills: [
                {
                    colSpan: "17 (1/2) -> 22 (1/2)",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Project 1",
        },
    ]);
    assert.verifySteps(["get_gantt_data", "with limit 2", "with offset 2"]);

    await click(target, ".o_pager_next");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "5-5");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "5");
    rows = getGridContent().rows;
    assert.deepEqual(rows, [
        {
            isGroup: true,
            pills: [
                {
                    colSpan: "20 -> 20 (1/2)",
                    title: "1",
                },
                {
                    colSpan: "27 -> 31",
                    title: "1",
                },
            ],
            title: "cancel",
        },
        {
            pills: [
                {
                    colSpan: "20 -> 20 (1/2)",
                    level: 0,
                    title: "Task 4",
                },
                {
                    colSpan: "27 -> 31",
                    level: 0,
                    title: "Task 3",
                },
            ],
            title: "Project 1",
        },
    ]);
    assert.verifySteps(["get_gantt_data", "with limit 2", "with offset 4"]);
});

QUnit.test("groups_limit attribute in sample mode (no groupBy)", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                groups_limit="2"
                sample="1"
            />
        `,
        domain: Domain.FALSE.toList(),
        mockRPC(_, { method, kwargs }) {
            assert.step(method);
            if (kwargs.limit) {
                assert.step(`with limit ${kwargs.limit}`);
            }
        },
    });

    assert.containsNone(target, ".o_gantt_view .o_control_panel .o_pager"); // only one group here!
    assert.verifySteps(["get_views", "get_gantt_data", "with limit 2"]);
});

QUnit.test("groups_limit attribute in sample mode (one groupBy)", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                groups_limit="2"
                sample="1"
            />
        `,
        domain: Domain.FALSE.toList(),
        groupBy: ["stage_id"],
        mockRPC(_, { method, kwargs }) {
            assert.step(method);
            if (kwargs.limit) {
                assert.step(`with limit ${kwargs.limit}`);
                assert.step(`with offset ${kwargs.offset}`);
            }
        },
    });

    assert.containsOnce(target, ".o_gantt_view .o_control_panel .o_pager");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "2");
    assert.containsN(target, ".o_gantt_row_title", 2);
    assert.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);
});

QUnit.test("groups_limit attribute in sample mode (two groupBys)", async (assert) => {
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: `
            <gantt
                date_start="start"
                date_stop="stop"
                groups_limit="2"
                sample="1"
            />
        `,
        domain: Domain.FALSE.toList(),
        groupBy: ["stage_id", "project_id"],
        mockRPC(_, { method, kwargs }) {
            assert.step(method);
            if (kwargs.limit) {
                assert.step(`with limit ${kwargs.limit}`);
                assert.step(`with offset ${kwargs.offset}`);
            }
        },
    });

    assert.containsOnce(target, ".o_gantt_view .o_control_panel .o_pager");
    assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
    assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "2");
    assert.verifySteps(["get_views", "get_gantt_data", "with limit 2", "with offset 0"]);
});

QUnit.test(
    "context in action should not override context added by the gantt view",
    async (assert) => {
        serverData.views["tasks,false,form"] = `
            <form>
                <field name="name"/>
                <field name="user_id"/>
                <field name="start"/>
                <field name="stop"/>
            </form>
        `;
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: `<gantt date_start="start" date_stop="stop" default_group_by="user_id" plan="false"/>`,
            context: {
                gantt_date: "2018-11-30",
                gantt_scale: "month",
                default_user_id: false,
            },
        });

        await hoverGridCell(1, 1, { ignoreHoverableClass: true });
        await clickCell(1, 1);
        assert.containsOnce(target, ".modal .o_field_many2one[name=user_id]");
        assert.strictEqual(
            target.querySelector(".modal .o_field_many2one[name=user_id] input").value,
            "User 1",
            "The user set should be the one in the row contained the cell clicked to add a record"
        );
    }
);

QUnit.test(
    "The date and task should appear even if the pill is planned on 2 days but displayed in one day by the gantt view",
    async (assert) => {
        patchDate(2024, 0, 1, 8, 0, 0);
        patchWithCleanup(luxon.Settings, {
            defaultZone: new luxon.IANAZone("UTC"),
        });
        serverData.models.tasks.records.push(
            {
                id: 9,
                name: "Task 9",
                allocated_hours: 4,
                start: "2024-01-01 16:00:00",
                stop: "2024-01-02 01:00:00",
            },
            {
                id: 10,
                name: "Task 10",
                allocated_hours: 4,
                start: "2024-01-02 16:00:00",
                stop: "2024-01-03 02:00:00",
            },
            {
                // will be displayed in 2 days
                id: 11,
                name: "Task 11",
                allocated_hours: 4,
                start: "2024-01-03 16:00:00",
                stop: "2024-01-04 03:00:00",
            }
        );
        await makeView({
            type: "gantt",
            resModel: "tasks",
            serverData,
            arch: `<gantt date_start="start"
                          date_stop="stop"
                          pill_label="True"
                          default_scale="week"
                          scales="week"
                          precision="{'week': 'day:full'}"
                    >
                    <field name="allocated_hours"/>
                </gantt>`,
        });
        assert.containsN(target, ".o_gantt_pill", 3, "should have 3 pills in the gantt view");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_gantt_pill_title")), [
            "4:00 PM - 1:00 AM (4h) - Task 9",
            "4:00 PM - 2:00 AM (4h) - Task 10",
            "Task 11",
        ]);
    }
);

// MANUAL TESTING

QUnit.skip("[FOR MANUAL TESTING] large amount of records (ungrouped)", async (assert) => {
    assert.expect(0);

    const NB_TASKS = 10000;

    serverData.models.tasks.records = [...Array(NB_TASKS)].map((_, i) => ({
        id: i + 1,
        name: `Task ${i + 1}`,
        start: `2018-12-01 00:00:00`,
        stop: `2018-12-01 23:00:00`,
    }));

    console.time("makeView");
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
    });
    console.timeEnd("makeView");
});

QUnit.skip("[FOR MANUAL TESTING] large amount of records (one level grouped)", async (assert) => {
    assert.expect(0);

    const NB_USERS = 10000;
    const NB_TASKS = 10000;

    serverData.models.users.records = [...Array(NB_USERS)].map((_, i) => ({
        id: i + 1,
        name: `${randomName(Math.floor(Math.random() * 8) + 8)} (${i + 1})`,
    }));
    serverData.models.tasks.records = [...Array(NB_TASKS)].map((_, i) => {
        let day1 = (i % 30) + 1;
        let day2 = (i % 30) + 2;
        if (day1 < 10) {
            day1 = "0" + day1;
        }
        if (day2 < 10) {
            day2 = "0" + day2;
        }
        return {
            id: i + 1,
            name: `Task ${i + 1}`,
            user_id: Math.floor(Math.random() * Math.floor(NB_USERS)) + 1,
            start: `2018-12-${day1}`,
            stop: `2018-12-${day2}`,
        };
    });

    console.time("makeView");
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["user_id"],
    });
    console.timeEnd("makeView");

    target.querySelector(".o_content").style = "max-height: 600px; overflow-y: scroll;";
});

QUnit.skip("[FOR MANUAL TESTING] large amount of records (two level grouped)", async (assert) => {
    assert.expect(0);

    const NB_USERS = 100;
    const NB_TASKS = 10000;
    const STAGES = serverData.models.tasks.fields.stage.selection;

    serverData.models.users.records = [...Array(NB_USERS)].map((_, i) => ({
        id: i + 1,
        name: `${randomName(Math.floor(Math.random() * 8) + 8)} (${i + 1})`,
    }));
    serverData.models.tasks.records = [...Array(NB_TASKS)].map((_, i) => ({
        id: i + 1,
        name: `Task ${i + 1}`,
        stage: STAGES[i % 2][0],
        user_id: (i % NB_USERS) + 1,
        start: "2018-12-01 00:00:00",
        stop: "2018-12-02 00:00:00",
    }));

    console.time("makeView");
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["user_id", "stage"],
    });
    console.timeEnd("makeView");
});

QUnit.test("group tasks by task_properties", async (assert) => {
    assert.expect(1);
    serverData.models.tasks.fields.task_properties = {
        string: "Properties",
        type: "properties",
        definition_record: "project_id",
        definition_record_field: "properties_definitions",
    };
    serverData.models.tasks.records = [
        {
            id: 1,
            name: "Blop",
            start: "2018-12-14 08:00:00",
            stop: "2018-12-24 08:00:00",
            user_id: 100,
            project_id: 1,
            task_properties: [
                {
                    name: "bd6404492c244cff",
                    type: "char",
                    value: "test value 1",
                },
            ],
        },
        {
            id: 2,
            name: "Yop",
            start: "2018-12-02 08:00:00",
            stop: "2018-12-12 08:00:00",
            user_id: 101,
            project_id: 1,
            task_properties: [
                {
                    name: "bd6404492c244cff",
                    type: "char",
                    value: "test value 1",
                },
            ],
        },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["task_properties.bd6404492c244cff"],
    });
    const { rows } = getGridContent();
    assert.deepEqual(
        rows,
        [
            {
                pills: [
                    {
                        title: "Yop",
                        colSpan: "02 -> 12 (1/2)",
                        level: 0,
                    },
                    {
                        title: "Blop",
                        colSpan: "14 -> 24 (1/2)",
                        level: 0,
                    },
                ],
            },
        ],
        "Rows should contain two records as we do not group by fields.properties"
    );
});

QUnit.test("group tasks by datetime", async (assert) => {
    assert.expect(1);
    serverData.models.tasks.fields.my_date = {
        string: "My date",
        type: "datetime",
    };
    serverData.models.tasks.records = [
        {
            id: 1,
            name: "Blop",
            start: "2018-12-14 08:00:00",
            stop: "2018-12-24 08:00:00",
            user_id: 100,
            project_id: 1,
        },
        {
            id: 2,
            name: "Yop",
            start: "2018-12-02 08:00:00",
            stop: "2018-12-12 08:00:00",
            user_id: 101,
            project_id: 1,
        },
    ];
    await makeView({
        type: "gantt",
        resModel: "tasks",
        serverData,
        arch: '<gantt date_start="start" date_stop="stop" />',
        groupBy: ["my_date:month"],
    });
    const { rows } = getGridContent();
    assert.deepEqual(
        rows,
        [
            {
                pills: [
                    {
                        title: "Yop",
                        colSpan: "02 -> 12 (1/2)",
                        level: 0,
                    },
                    {
                        title: "Blop",
                        colSpan: "14 -> 24 (1/2)",
                        level: 0,
                    },
                ],
            },
        ],
    );
});
