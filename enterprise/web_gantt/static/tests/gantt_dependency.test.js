import { beforeEach, describe, expect, queryOne, test } from "@odoo/hoot";
import { hover, pointerDown, queryAll, queryFirst, queryRect, resize } from "@odoo/hoot-dom";
import { advanceFrame, animationFrame, mockDate, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    findComponent,
    models,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    clickConnectorButton,
    getConnector,
    getConnectorMap,
    getConnectorStroke,
} from "@web_gantt/../tests/gantt_dependency_helpers";
import { COLORS } from "@web_gantt/gantt_connector";
import {
    CLASSES,
    SELECTORS,
    getPill,
    getPillWrapper,
    mountGanttView,
} from "./web_gantt_test_helpers";

import { GanttRenderer } from "@web_gantt/gantt_renderer";

/** @typedef {import("@web_gantt/gantt_renderer").ConnectorProps} ConnectorProps */
/** @typedef {import("@web_gantt/gantt_renderer").PillId} PillId */

/**
 * @typedef {`[${ResId},${ResId},${ResId},${ResId}]`} ConnectorTaskIds
 * In the following order: [masterTaskId, masterTaskUserId, taskId, taskUserId]
 */

/** @typedef {number | false} ResId */

const ganttViewParams = {
    resModel: "project.task",
    arch: /* xml */ `<gantt date_start="planned_date_begin" date_stop="date_deadline" default_scale="month" dependency_field="depend_on_ids" color="color" />`,
    groupBy: ["user_ids"],
};

let nextColor = 1;
class ProjectTask extends models.Model {
    _name = "project.task";

    name = fields.Char();
    planned_date_begin = fields.Datetime({ string: "Start Date" });
    date_deadline = fields.Datetime({ string: "Stop Date" });
    user_ids = fields.Many2many({ string: "Assignees", relation: "res.users" });
    allow_task_dependencies = fields.Boolean({ default: true });
    depend_on_ids = fields.One2many({ string: "Depends on", relation: "project.task" });
    display_warning_dependency_in_gantt = fields.Boolean({ default: true });
    color = fields.Integer({ default: () => nextColor++ });

    _records = [
        {
            id: 1,
            name: "Task 1",
            planned_date_begin: "2021-10-11 18:30:00",
            date_deadline: "2021-10-11 19:29:59",
            user_ids: [1],
            depend_on_ids: [],
        },
        {
            id: 2,
            name: "Task 2",
            planned_date_begin: "2021-10-12 11:30:00",
            date_deadline: "2021-10-12 12:29:59",
            user_ids: [1, 3],
            depend_on_ids: [1],
        },
        {
            id: 3,
            name: "Task 3",
            planned_date_begin: "2021-10-13 06:30:00",
            date_deadline: "2021-10-13 07:29:59",
            user_ids: [],
            depend_on_ids: [2],
        },
        {
            id: 4,
            name: "Task 4",
            planned_date_begin: "2021-10-14 22:30:00",
            date_deadline: "2021-10-14 23:29:59",
            user_ids: [2, 3],
            depend_on_ids: [2],
        },
        {
            id: 5,
            name: "Task 5",
            planned_date_begin: "2021-10-15 01:53:10",
            date_deadline: "2021-10-15 02:34:34",
            user_ids: [],
            depend_on_ids: [],
        },
        {
            id: 6,
            name: "Task 6",
            planned_date_begin: "2021-10-16 23:00:00",
            date_deadline: "2021-10-16 23:21:01",
            user_ids: [1, 3],
            depend_on_ids: [4, 5],
        },
        {
            id: 7,
            name: "Task 7",
            planned_date_begin: "2021-10-17 10:30:12",
            date_deadline: "2021-10-17 11:29:59",
            user_ids: [1, 2, 3],
            depend_on_ids: [6],
        },
        {
            id: 8,
            name: "Task 8",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-18 07:29:59",
            user_ids: [1, 3],
            depend_on_ids: [7],
        },
        {
            id: 9,
            name: "Task 9",
            planned_date_begin: "2021-10-19 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [8],
        },
        {
            id: 10,
            name: "Task 10",
            planned_date_begin: "2021-10-19 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [],
        },
        {
            id: 11,
            name: "Task 11",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-18 07:29:59",
            user_ids: [2],
            depend_on_ids: [10],
        },
        {
            id: 12,
            name: "Task 12",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [],
        },
        {
            id: 13,
            name: "Task 13",
            planned_date_begin: "2021-10-18 07:29:59",
            date_deadline: "2021-10-20 07:29:59",
            user_ids: [2],
            depend_on_ids: [12],
        },
    ];
}

class ResUsers extends models.Model {
    _name = "res.users";

    name = fields.Char();

    _records = [
        { id: 1, name: "User 1" },
        { id: 2, name: "User 2" },
        { id: 3, name: "User 3" },
        { id: 4, name: "User 4" },
    ];
}

defineModels([ProjectTask, ResUsers]);

describe.current.tags("desktop");

beforeEach(() => mockDate("2021-10-10T08:00:00", +1));

test("Connectors are correctly computed and rendered.", async () => {
    /**
     * @type {Map<ConnectorTaskIds, keyof typeof COLORS>}
     * =>  Check that there is a connector between masterTaskId from group masterTaskUserId and taskId from group taskUserId with normal|error color.
     */
    const testMap = new Map([
        ["[1,1,2,1]", "default"],
        ["[1,1,2,3]", "default"],
        ["[2,1,3,false]", "default"],
        ["[2,3,3,false]", "default"],
        ["[2,1,4,2]", "default"],
        ["[2,3,4,3]", "default"],
        ["[4,2,6,1]", "default"],
        ["[4,3,6,3]", "default"],
        ["[5,false,6,1]", "default"],
        ["[5,false,6,3]", "default"],
        ["[6,1,7,1]", "default"],
        ["[6,1,7,2]", "default"],
        ["[6,3,7,2]", "default"],
        ["[6,3,7,3]", "default"],
        ["[7,1,8,1]", "default"],
        ["[7,2,8,1]", "default"],
        ["[7,2,8,3]", "default"],
        ["[7,3,8,3]", "default"],
        ["[8,1,9,2]", "default"],
        ["[8,3,9,2]", "default"],
        ["[10,2,11,2]", "error"],
        ["[12,2,13,2]", "warning"],
    ]);

    const view = await mountGanttView(ganttViewParams);
    const renderer = findComponent(view, (c) => c instanceof GanttRenderer);

    const connectorMap = getConnectorMap(renderer);

    for (const [testKey, colorCode] of testMap.entries()) {
        const [masterTaskId, masterTaskUserId, taskId, taskUserId] = JSON.parse(testKey);

        expect(connectorMap.has(testKey)).toBe(true, {
            message: `There should be a connector between task ${masterTaskId} from group user ${masterTaskUserId} and task ${taskId} from group user ${taskUserId}.`,
        });

        const connector = connectorMap.get(testKey);
        expect(getConnector(connector.id)).toHaveCount(1);
        expect(getConnectorStroke(connector.id)).toHaveAttribute("stroke", COLORS[colorCode].color);
    }

    expect(testMap).toHaveLength(connectorMap.size);
    expect(SELECTORS.connector).toHaveCount(testMap.size);
});

test("Connectors are correctly rendered.", async () => {
    patchWithCleanup(GanttRenderer.prototype, {
        shouldRenderRecordConnectors(record) {
            return record.id !== 1;
        },
    });

    ProjectTask._records = [
        {
            id: 1,
            name: "Task 1",
            planned_date_begin: "2021-10-11 18:30:00",
            date_deadline: "2021-10-11 19:29:59",
            user_ids: [1],
            depend_on_ids: [],
        },
        {
            id: 2,
            name: "Task 2",
            planned_date_begin: "2021-10-12 11:30:00",
            date_deadline: "2021-10-12 12:29:59",
            user_ids: [1],
            depend_on_ids: [1],
        },
        {
            id: 3,
            name: "Task 3",
            planned_date_begin: "2021-10-13 06:30:00",
            date_deadline: "2021-10-13 07:29:59",
            user_ids: [],
            depend_on_ids: [1, 2],
        },
    ];

    const view = await mountGanttView(ganttViewParams);
    const renderer = findComponent(view, (c) => c instanceof GanttRenderer);
    const connectorMap = getConnectorMap(renderer);
    expect([...connectorMap.keys()]).toEqual(["[2,1,3,false]"], {
        message: "The only rendered connector should be the one from task_id 2 to task_id 3",
    });
});

test("Connectors are correctly computed and rendered when consolidation is active.", async () => {
    ProjectTask._records = [
        {
            id: 1,
            name: "Task 1",
            planned_date_begin: "2021-10-11 18:30:00",
            date_deadline: "2021-10-11 19:29:59",
            user_ids: [1],
            depend_on_ids: [],
        },
        {
            id: 2,
            name: "Task 2",
            planned_date_begin: "2021-10-12 11:30:00",
            date_deadline: "2021-10-12 12:29:59",
            user_ids: [1, 3],
            depend_on_ids: [1],
        },
        {
            id: 3,
            name: "Task 3",
            planned_date_begin: "2021-10-13 06:30:00",
            date_deadline: "2021-10-13 07:29:59",
            user_ids: [],
            depend_on_ids: [2],
        },
        {
            id: 4,
            name: "Task 4",
            planned_date_begin: "2021-10-14 22:30:00",
            date_deadline: "2021-10-14 23:29:59",
            user_ids: [2, 3],
            depend_on_ids: [2],
        },
        {
            id: 5,
            name: "Task 5",
            planned_date_begin: "2021-10-15 01:53:10",
            date_deadline: "2021-10-15 02:34:34",
            user_ids: [],
            depend_on_ids: [],
        },
        {
            id: 6,
            name: "Task 6",
            planned_date_begin: "2021-10-16 23:00:00",
            date_deadline: "2021-10-16 23:21:01",
            user_ids: [1, 3],
            depend_on_ids: [4, 5],
        },
        {
            id: 7,
            name: "Task 7",
            planned_date_begin: "2021-10-17 10:30:12",
            date_deadline: "2021-10-17 11:29:59",
            user_ids: [1, 2, 3],
            depend_on_ids: [6],
        },
        {
            id: 8,
            name: "Task 8",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-18 07:29:59",
            user_ids: [1, 3],
            depend_on_ids: [7],
        },
        {
            id: 9,
            name: "Task 9",
            planned_date_begin: "2021-10-19 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [8],
        },
        {
            id: 10,
            name: "Task 10",
            planned_date_begin: "2021-10-19 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [],
        },
        {
            id: 11,
            name: "Task 11",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-18 07:29:59",
            user_ids: [2],
            depend_on_ids: [10],
        },
        {
            id: 12,
            name: "Task 12",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [],
        },
        {
            id: 13,
            name: "Task 13",
            planned_date_begin: "2021-10-18 07:29:59",
            date_deadline: "2021-10-20 07:29:59",
            user_ids: [2],
            depend_on_ids: [12],
        },
    ];

    await mountGanttView({
        ...ganttViewParams,
        arch: /* xml */ `<gantt date_start="planned_date_begin" date_stop="date_deadline" default_scale="month" dependency_field="depend_on_ids" consolidation_max="{'user_ids': 100 }"/>`,
    });

    // groups have been created of r
    expect(".o_gantt_row_header.o_gantt_group.o_group_open").toHaveCount(4);

    function getGroupRow(index) {
        return queryAll(".o_gantt_row_header.o_gantt_group")[index];
    }

    expect(SELECTORS.connector).toHaveCount(22);

    await contains(getGroupRow(1)).click();
    expect(getGroupRow(1)).not.toHaveClass("o_group_open");
    expect(SELECTORS.connector).toHaveCount(13);

    await contains(getGroupRow(1)).click();
    expect(SELECTORS.connector).toHaveCount(22);

    await contains(getGroupRow(1)).click();
    expect(SELECTORS.connector).toHaveCount(13);

    await contains(getGroupRow(2)).click();
    expect(SELECTORS.connector).toHaveCount(6);

    await contains(getGroupRow(0)).click();
    expect(SELECTORS.connector).toHaveCount(4);

    await contains(getGroupRow(3)).click();
    expect(SELECTORS.connector).toHaveCount(0);
});

test("Connector hovered state is triggered and color is set accordingly.", async () => {
    await mountGanttView(ganttViewParams);

    expect(getConnector(1)).not.toHaveClass(CLASSES.highlightedConnector);
    expect(getConnectorStroke(1)).toHaveAttribute("stroke", COLORS.default.color);

    await hover(getConnectorStroke(1));
    await animationFrame();

    expect(getConnector(1)).toHaveClass(CLASSES.highlightedConnector);
    expect(getConnectorStroke(1)).toHaveAttribute("stroke", COLORS.default.highlightedColor);
});

test("Buttons are displayed when hovering a connector.", async () => {
    await mountGanttView(ganttViewParams);
    expect(queryAll(SELECTORS.connectorStrokeButton, { root: getConnector(1) })).toHaveCount(0);

    await hover(getConnectorStroke(1));
    await animationFrame();

    expect(queryAll(SELECTORS.connectorStrokeButton, { root: getConnector(1) })).toHaveCount(3);
});

test("Buttons are displayed when hovering a connector after a pill has been hovered.", async () => {
    await mountGanttView(ganttViewParams);
    expect(queryAll(SELECTORS.connectorStrokeButton, { root: getConnector(1) })).toHaveCount(0);

    await hover(getPill("Task 1"));
    await animationFrame();

    expect(queryAll(SELECTORS.connectorStrokeButton, { root: getConnector(1) })).toHaveCount(0);
    expect(getConnector(1)).toHaveClass(CLASSES.highlightedConnector);

    await hover(getConnectorStroke(1));
    await animationFrame();

    expect(getConnector(1)).toHaveClass(CLASSES.highlightedConnector);
    expect(queryAll(SELECTORS.connectorStrokeButton, { root: getConnector(1) })).toHaveCount(3);
});

test("Connector buttons: remove a dependency", async () => {
    onRpc(({ method, model, args }) => {
        if (model === "project.task" && ["web_gantt_reschedule", "write"].includes(method)) {
            expect.step([method, args]);
            return true;
        }
    });
    await mountGanttView(ganttViewParams);

    await clickConnectorButton(getConnector(1), "remove");
    expect.verifySteps([["write", [[2], { depend_on_ids: [[3, 1, false]] }]]]);
});

test("Connector buttons: reschedule task backward date.", async () => {
    onRpc(({ method, model, args }) => {
        if (model === "project.task" && ["web_gantt_reschedule", "write"].includes(method)) {
            expect.step([method, args]);
            return {};
        }
    });
    await mountGanttView(ganttViewParams);

    await clickConnectorButton(getConnector(1), "reschedule-backward");
    expect.verifySteps([
        [
            "web_gantt_reschedule",
            ["backward", 1, 2, "depend_on_ids", null, "planned_date_begin", "date_deadline"],
        ],
    ]);
});

test("Connector buttons: reschedule task forward date.", async () => {
    onRpc(({ args, method, model }) => {
        if (model === "project.task" && ["web_gantt_reschedule", "write"].includes(method)) {
            expect.step([method, args]);
            return {};
        }
    });
    await mountGanttView(ganttViewParams);

    await clickConnectorButton(getConnector(1), "reschedule-forward");
    expect.verifySteps([
        [
            "web_gantt_reschedule",
            ["forward", 1, 2, "depend_on_ids", null, "planned_date_begin", "date_deadline"],
        ],
    ]);
});

test("Connector buttons: reschedule task start backward, different data.", async () => {
    onRpc(({ method, model, args }) => {
        if (model === "project.task" && ["web_gantt_reschedule", "write"].includes(method)) {
            expect.step([method, args]);
            return {};
        }
    });
    await mountGanttView(ganttViewParams);

    await clickConnectorButton(getConnector(1), "reschedule-backward");
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification .o_notification_buttons button").toHaveCount(0, {
        message:
            "No button should be displayed in the notification since `old_vals_per_pill_id` is not given in the result of `web_gantt_reschedule` call",
    });
    expect.verifySteps([
        [
            "web_gantt_reschedule",
            ["backward", 1, 2, "depend_on_ids", null, "planned_date_begin", "date_deadline"],
        ],
    ]);
});

test("Connector buttons: reschedule task forward, different data.", async () => {
    onRpc(({ method, model, args }) => {
        if (model === "project.task" && ["web_gantt_reschedule", "write"].includes(method)) {
            expect.step([method, args]);
            return {};
        }
    });
    await mountGanttView(ganttViewParams);

    await clickConnectorButton(getConnector(1), "reschedule-forward");
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification .o_notification_buttons button").toHaveCount(0, {
        message:
            "No button should be displayed in the notification since `old_vals_per_pill_id` is not given in the result of `web_gantt_reschedule` call",
    });
    expect.verifySteps([
        [
            "web_gantt_reschedule",
            ["forward", 1, 2, "depend_on_ids", null, "planned_date_begin", "date_deadline"],
        ],
    ]);
});

test("Connector buttons: reschedule task forward and undo.", async () => {
    onRpc(({ method, model, args }) => {
        if (
            model === "project.task" &&
            ["web_gantt_reschedule", "action_rollback_scheduling"].includes(method)
        ) {
            expect.step([method, args]);
            return { old_vals_per_pill_id: { 1: { test: true }, 2: { foo: false } } };
        }
    });
    await mountGanttView(ganttViewParams);

    await clickConnectorButton(getConnector(1), "reschedule-forward");
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification .o_notification_buttons button").toHaveCount(1);
    await contains(".o_notification .o_notification_buttons button i.fa-undo").click();
    expect.verifySteps([
        [
            "web_gantt_reschedule",
            ["forward", 1, 2, "depend_on_ids", null, "planned_date_begin", "date_deadline"],
        ],
        ["action_rollback_scheduling", [[1, 2], { 1: { test: true }, 2: { foo: false } }]],
    ]);
});

test("Hovering a task pill should highlight related tasks and dependencies", async () => {
    /** @type {Map<ConnectorTaskIds, boolean>} */
    const testMap = new Map([
        ["[1,1,2,1]", true],
        ["[1,1,2,3]", true],
        ["[2,1,3,false]", true],
        ["[2,3,3,false]", true],
        ["[2,1,4,2]", true],
        ["[2,3,4,3]", true],
        ["[10,2,11,2]", false],
    ]);

    ProjectTask._records = [
        {
            id: 1,
            name: "Task 1",
            planned_date_begin: "2021-10-10 18:30:00",
            date_deadline: "2021-10-11 19:29:59",
            user_ids: [1],
            depend_on_ids: [],
        },
        {
            id: 2,
            name: "Task 2",
            planned_date_begin: "2021-10-12 11:30:00",
            date_deadline: "2021-10-12 12:29:59",
            user_ids: [1, 3],
            depend_on_ids: [1],
        },
        {
            id: 3,
            name: "Task 3",
            planned_date_begin: "2021-10-13 06:30:00",
            date_deadline: "2021-10-13 07:29:59",
            user_ids: [],
            depend_on_ids: [2],
        },
        {
            id: 4,
            name: "Task 4",
            planned_date_begin: "2021-10-14 22:30:00",
            date_deadline: "2021-10-14 23:29:59",
            user_ids: [2, 3],
            depend_on_ids: [2],
        },
        {
            id: 10,
            name: "Task 10",
            planned_date_begin: "2021-10-19 06:30:12",
            date_deadline: "2021-10-19 07:29:59",
            user_ids: [2],
            depend_on_ids: [],
            display_warning_dependency_in_gantt: false,
        },
        {
            id: 11,
            name: "Task 11",
            planned_date_begin: "2021-10-18 06:30:12",
            date_deadline: "2021-10-18 07:29:59",
            user_ids: [2],
            depend_on_ids: [10],
        },
    ];

    const view = await mountGanttView(ganttViewParams);
    const renderer = findComponent(view, (c) => c instanceof GanttRenderer);

    const connectorMap = getConnectorMap(renderer);
    const pills = [];
    for (const wrapper of queryAll(SELECTORS.pillWrapper)) {
        const pillId = wrapper.dataset.pillId;
        pills.push({
            el: queryFirst(SELECTORS.pill, { root: wrapper }),
            recordId: renderer.pills[pillId].record.id,
        });
    }

    const task2Pills = pills.filter((p) => p.recordId === 2);

    expect(task2Pills).toHaveLength(2);
    expect(CLASSES.highlightedPill).toHaveCount(0);

    // Check that all connectors are not in hover state.
    for (const testKey of testMap.keys()) {
        expect(getConnector(connectorMap.get(testKey).id)).not.toHaveClass(
            CLASSES.highlightedConnector
        );
    }

    await contains(getPill("Task 2", { nth: 1 })).hover();
    // Both pills should be highlighted
    expect(getPillWrapper("Task 2", { nth: 1 })).toHaveClass(CLASSES.highlightedPill);
    expect(getPillWrapper("Task 2", { nth: 2 })).toHaveClass(CLASSES.highlightedPill);

    // The rest of the pills should not be highlighted nor display connector creators
    for (const { el, recordId } of pills) {
        if (recordId !== 2) {
            expect(el).not.toHaveClass(CLASSES.highlightedPill);
        }
    }

    // Check that all connectors are in the expected hover state.
    for (const [testKey, shouldBeHighlighted] of testMap.entries()) {
        const connector = getConnector(connectorMap.get(testKey).id);
        if (shouldBeHighlighted) {
            expect(connector).toHaveClass(CLASSES.highlightedConnector);
        } else {
            expect(connector).not.toHaveClass(CLASSES.highlightedConnector);
        }
        expect(queryAll(SELECTORS.connectorStrokeButton, { root: connector })).toHaveCount(0);
    }
});

test("Hovering a connector should cause the connected pills to get highlighted.", async () => {
    await mountGanttView(ganttViewParams);
    expect(SELECTORS.highlightedConnector).toHaveCount(0);
    expect(SELECTORS.highlightedPill).toHaveCount(0);

    await hover(getConnectorStroke(1));
    await animationFrame();

    expect(SELECTORS.highlightedConnector).toHaveCount(1);
    expect(SELECTORS.highlightedPill).toHaveCount(2);
});

test("Connectors are displayed behind pills, except on hover.", async () => {
    const getZIndex = (el) => Number(getComputedStyle(queryFirst(el)).zIndex) || 0;

    await mountGanttView(ganttViewParams);
    expect(getZIndex(getPillWrapper("Task 2"))).toBeGreaterThan(getZIndex(getConnector(1)));

    await hover(getConnectorStroke(1));
    await animationFrame();

    expect(getZIndex(getPillWrapper("Task 2"))).toBeLessThan(getZIndex(getConnector(1)));
});

test("Create a connector from the gantt view.", async () => {
    onRpc("write", ({ args, method }) => expect.step([method, args]));
    await mountGanttView(ganttViewParams);

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst(SELECTORS.connectorCreatorWrapper);
    rightWrapper.classList.add("d-block");

    await contains(
        `${SELECTORS.connectorCreatorWrapper} ${SELECTORS.connectorCreatorBullet}:first`
    ).dragAndDrop(getPill("Task 2"));
    expect.verifySteps([["write", [[2], { depend_on_ids: [[4, 3, false]] }]]]);
});

test("Create a connector from the gantt view: going fast", async () => {
    await mountGanttView({
        ...ganttViewParams,
        domain: [["id", "in", [1, 3]]],
    });

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst(SELECTORS.connectorCreatorWrapper, {
        root: getPillWrapper("Task 1"),
    });
    rightWrapper.classList.add("d-block");

    const connectorBullet = queryFirst(SELECTORS.connectorCreatorBullet, { root: rightWrapper });
    const bulletRect = queryRect(connectorBullet);
    const initialPosition = {
        x: Math.floor(bulletRect.left + bulletRect.width / 2), // floor to avoid sub-pixel positioning
        y: Math.floor(bulletRect.top + bulletRect.height / 2), // floor to avoid sub-pixel positioning
    };
    await pointerDown(connectorBullet, {
        position: { clientX: initialPosition.x, clientY: initialPosition.y },
    });

    // Here we simulate a fast move, using arbitrary values.
    const currentPosition = {
        x: Math.floor(initialPosition.x + 123), // floor to avoid sub-pixel positioning
        y: Math.floor(initialPosition.y + 12), // floor to avoid sub-pixel positioning
    };
    await hover(SELECTORS.cellContainer, {
        position: { clientX: currentPosition.x, clientY: currentPosition.y },
    });
    await animationFrame();

    // Then we check that the connector stroke is correctly positioned.
    expect(getConnectorStroke("new")).toHaveRect({
        top: initialPosition.y,
        right: currentPosition.x,
        bottom: currentPosition.y,
        left: initialPosition.x,
    });
});

test("Connectors should be rendered if connected pill is not visible", async () => {
    // We first need to bump all the ids for users 2, 3 and 4 to make them disappear.
    for (const record of ResUsers._records.slice(1)) {
        record.id += 1000;
    }
    for (const record of ProjectTask._records) {
        record.user_ids = record.user_ids.map((id) => (id > 1 ? id + 1000 : id));
    }
    // Generate a lot of users so that the connectors are far beyond the visible
    // viewport, hence generating fake extra pills to render the connectors.
    for (let i = 0; i < 100; i++) {
        const id = 100 + i;
        ResUsers._records.push({ id, name: `User ${id}` });
        ProjectTask._records.push({
            id,
            name: `Task ${id}`,
            planned_date_begin: "2021-10-11 18:30:00",
            date_deadline: "2021-10-11 19:29:59",
            user_ids: [id],
            depend_on_ids: [],
        });
    }
    ProjectTask._records[12].user_ids = [199];

    await mountGanttView(ganttViewParams);
    expect(queryAll(SELECTORS.connector, { visible: true })).toHaveCount(13);
});

test("No display of resize handles when creating a connector", async () => {
    await mountGanttView(ganttViewParams);

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst(SELECTORS.connectorCreatorWrapper);
    rightWrapper.classList.add("d-block");

    // Creating a connector and hover another pill while dragging it
    const { cancel, moveTo } = await contains(SELECTORS.connectorCreatorBullet, {
        root: rightWrapper,
    }).drag();
    await moveTo(getPill("Task 2"));

    expect(SELECTORS.resizeHandle).toHaveCount(0);

    await cancel();
});

test("Renderer in connect mode when creating a connector", async () => {
    await mountGanttView(ganttViewParams);

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst(SELECTORS.connectorCreatorWrapper);
    rightWrapper.classList.add("d-block");

    // Creating a connector and hover another pill while dragging it
    const { cancel, moveTo } = await contains(SELECTORS.connectorCreatorBullet, {
        root: rightWrapper,
    }).drag();
    await moveTo(getPill("Task 2"));

    expect(SELECTORS.renderer).toHaveClass("o_connect");

    await cancel();
});

test("Connector creators of initial pill are highlighted when creating a connector", async () => {
    await mountGanttView(ganttViewParams);

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst`${SELECTORS.pillWrapper} ${SELECTORS.connectorCreatorWrapper}`;
    rightWrapper.classList.add("d-block");

    // Creating a connector and hover another pill while dragging it
    const { cancel, moveTo } = await contains(SELECTORS.connectorCreatorBullet, {
        root: rightWrapper,
    }).drag();
    await moveTo(getPill("Task 2"));

    expect(`${SELECTORS.pillWrapper}:first`).toHaveClass(CLASSES.lockedConnectorCreator);

    await cancel();
});

test("Connector creators of hovered pill are highlighted when creating a connector", async () => {
    await mountGanttView(ganttViewParams);

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst(SELECTORS.connectorCreatorWrapper);
    rightWrapper.classList.add("d-block");

    // Creating a connector and hover another pill while dragging it
    const { cancel, moveTo } = await contains(SELECTORS.connectorCreatorBullet, {
        root: rightWrapper,
    }).drag();

    const destinationWrapper = getPillWrapper("Task 2");
    const destinationPill = queryFirst(SELECTORS.pill, { root: destinationWrapper });
    await moveTo(destinationPill);

    // moveTo only triggers a pointerenter event on destination pill,
    // a pointermove event is still needed to highlight it
    await contains(destinationPill).hover();
    expect(destinationWrapper).toHaveClass(CLASSES.highlightedConnectorCreator);

    await cancel();
});

test("Switch to full-size browser: the connections between pills should be diplayed", async () => {
    await resize({ width: 375, height: 667 });

    await mountGanttView(ganttViewParams);

    // Mobile view
    expect("svg.o_gantt_connector").toHaveCount(0, {
        message: "Gantt connectors should not be visible in small/mobile view",
    });

    // Resizing browser to leave mobile view
    await resize({ width: 1366, height: 768 });
    await runAllTimers();

    expect("svg.o_gantt_connector").toHaveCount(22, {
        message: "Gantt connectors should be visible when switching to desktop view",
    });
});

test.tags("broken");
test("Connect two very distant pills", async () => {
    ProjectTask._records = [
        ProjectTask._records[0],
        {
            id: 2,
            name: "Task 2",
            planned_date_begin: "2021-11-18 08:00:00",
            date_deadline: "2021-11-18 16:00:00",
            user_ids: [2],
            depend_on_ids: [],
        },
    ];
    onRpc("write", ({ args }) => {
        expect.step(args);
    });
    await mountGanttView({
        ...ganttViewParams,
        context: {
            default_start_date: "2021-10-01",
            default_stop_date: "2021-11-30",
        },
    });
    expect(SELECTORS.connector).toHaveCount(0);

    // Explicitly shows the connector creator wrapper since its "display: none"
    // disappears on native CSS hover, which cannot be programatically emulated.
    const rightWrapper = queryFirst(SELECTORS.connectorCreatorWrapper);
    rightWrapper.classList.add("d-block");

    // Creating a connector and hover another pill while dragging it
    const { drop, moveTo } = await contains(SELECTORS.connectorCreatorBullet, {
        root: rightWrapper,
    }).drag();

    const selector = `${SELECTORS.pill}:contains('Task 2')`;
    expect(selector).toHaveCount(0);
    await moveTo({ position: { x: window.innerWidth * 2 } });
    await advanceFrame(200);

    // FIXME: ELEMENT SHOULD BE INTERACTIVE -> test is simulating a situation that
    // cannot happen. Investigate the issue, remove the following line and the
    // "broken" tag when fixed.
    queryOne(selector).classList.add("pe-auto");

    await drop(selector);
    expect.verifySteps([[[2], { depend_on_ids: [[4, 1, false]] }]]);
    expect(SELECTORS.connector).toHaveCount(1);
});
