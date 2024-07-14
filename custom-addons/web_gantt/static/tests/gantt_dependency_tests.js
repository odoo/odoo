/** @odoo-module **/

import {
    click,
    dragAndDrop,
    drag,
    getFixture,
    patchDate,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { COLORS } from "@web_gantt/gantt_connector";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { CLASSES, SELECTORS, getPill, getPillWrapper } from "./helpers";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/** @typedef {import("@web_gantt/gantt_renderer").ConnectorProps} ConnectorProps */
/** @typedef {import("@web_gantt/gantt_renderer").PillId} PillId */

/**
 * @typedef {`[${ResId},${ResId},${ResId},${ResId}]`} ConnectorTaskIds
 * In the following order: [masterTaskId, masterTaskUserId, taskId, taskUserId]
 */

/** @typedef {number | false} ResId */

/**
 * @param {Element} connector
 * @param {"remove" | "reschedule-forward" | "reschedule-backward"} button
 */
async function clickConnectorButton(connector, button) {
    await triggerEvent(connector, null, "pointermove");
    switch (button) {
        case "remove": {
            return click(connector, SELECTORS.connectorRemoveButton);
        }
        case "reschedule-backward": {
            return click(connector, `${SELECTORS.connectorRescheduleButton}:first-of-type`);
        }
        case "reschedule-forward": {
            return click(connector, `${SELECTORS.connectorRescheduleButton}:last-of-type`);
        }
    }
}

/**
 * @param {number | "new"} id
 */
export function getConnector(id) {
    if (!/^__connector__/.test(id)) {
        id = `__connector__${id}`;
    }
    return getFixture().querySelector([
        `${SELECTORS.cellContainer} ${SELECTORS.connector}[data-connector-id='${id}']`,
    ]);
}

export function getConnectorMap(renderer) {
    /**
     * @param {PillId} pillId
     */
    const getIdAndUserIdFromPill = (pillId) => {
        /** @type {[ResId, ResId]} */
        const result = [renderer.pills[pillId]?.record.id || false, false];
        if (result[0]) {
            const pills = renderer.mappingRecordToPillsByRow[result[0]]?.pills;
            if (pills) {
                const pillEntry = Object.entries(pills).find((e) => e[1].id === pillId);
                if (pillEntry) {
                    const [firstGroup] = JSON.parse(pillEntry[0]);
                    if (firstGroup.user_ids?.length) {
                        result[1] = firstGroup.user_ids[0] || false;
                    }
                }
            }
        }
        return result;
    };

    /** @type {Map<ConnectorTaskIds, ConnectorProps>} */
    const connectorMap = new Map();
    for (const connector of Object.values(renderer.connectors)) {
        const { sourcePillId, targetPillId } = renderer.mappingConnectorToPills[connector.id];
        if (!sourcePillId || !targetPillId) {
            continue;
        }
        const key = JSON.stringify([
            ...getIdAndUserIdFromPill(sourcePillId),
            ...getIdAndUserIdFromPill(targetPillId),
        ]);
        connectorMap.set(key, connector);
    }
    return connectorMap;
}

const ganttViewParams = {
    type: "gantt",
    resModel: "project.task",
    arch: /* xml */ `
        <gantt
            date_start="planned_date_begin"
            date_stop="date_deadline"
            default_scale="month"
            dependency_field="depend_on_ids"
        />
    `,
};

/** @type {GanttRenderer} */
let renderer;
/** @type {HTMLElement} */
let target;

QUnit.module("Views > GanttView", (hooks) => {
    hooks.beforeEach(async () => {
        patchDate(2021, 9, 10, 8, 0, 0);
        patchWithCleanup(GanttRenderer.prototype, {
            setup() {
                super.setup(...arguments);
                renderer = this;
            },
        });

        setupViewRegistries();

        target = getFixture();
        ganttViewParams.serverData = {
            models: {
                "project.task": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        planned_date_begin: { string: "Start Date", type: "datetime" },
                        date_deadline: { string: "Stop Date", type: "datetime" },
                        user_ids: { string: "Assignees", type: "many2many", relation: "res.users" },
                        allow_task_dependencies: {
                            string: "Allow Task Dependencies",
                            type: "boolean",
                            default: true,
                        },
                        depend_on_ids: {
                            string: "Depends on",
                            type: "one2many",
                            relation: "project.task",
                        },
                        display_warning_dependency_in_gantt: {
                            string: "Display warning dependency in Gantt",
                            type: "boolean",
                            default: true,
                        },
                    },
                    records: [
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
                    ],
                },
                "res.users": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "User 1" },
                        { id: 2, name: "User 2" },
                        { id: 3, name: "User 3" },
                        { id: 4, name: "User 4" },
                    ],
                },
            },
        };

        ganttViewParams.groupBy = ["user_ids"];
    });

    QUnit.module("Dependencies");

    QUnit.test("Connectors are correctly computed and rendered.", async (assert) => {
        assert.expect(46);

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

        await makeView(ganttViewParams);

        const connectorMap = getConnectorMap(renderer);

        for (const [testKey, colorCode] of testMap.entries()) {
            const [masterTaskId, masterTaskUserId, taskId, taskUserId] = JSON.parse(testKey);

            assert.ok(
                connectorMap.has(testKey),
                `There should be a connector between task ${masterTaskId} from group user ${masterTaskUserId} and task ${taskId} from group user ${taskUserId}.`
            );

            const connector = connectorMap.get(testKey);
            const connectorStroke = getConnector(connector.id).querySelector(
                SELECTORS.connectorStroke
            );
            assert.hasAttrValue(connectorStroke, "stroke", COLORS[colorCode].color);
        }

        assert.strictEqual(testMap.size, connectorMap.size);
        assert.strictEqual(target.querySelectorAll(SELECTORS.connector).length, testMap.size);
    });

    QUnit.test("Connectors are correctly rendered.", async (assert) => {
        patchWithCleanup(GanttRenderer.prototype, {
            shouldRenderRecordConnectors(record) {
                return record.id !== 1;
            },
        });

        ganttViewParams.serverData.models["project.task"].records = [
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

        await makeView(ganttViewParams);
        const connectorMap = getConnectorMap(renderer);
        assert.deepEqual(
            [...connectorMap.keys()],
            ["[2,1,3,false]"],
            "The only rendered connector should be the one from task_id 2 to task_id 3"
        );
    });

    QUnit.test(
        "Connectors are correctly computed and rendered when consolidation is active.",
        async (assert) => {
            ganttViewParams.serverData.models["project.task"].records = [
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

            await makeView({
                ...ganttViewParams,
                arch: /* xml */ `
                    <gantt
                        date_start="planned_date_begin"
                        date_stop="date_deadline"
                        default_scale="month"
                        dependency_field="depend_on_ids"
                        consolidation_max="{'user_ids': 100 }"
                    />
                `,
            });

            // groups have been created of r
            assert.strictEqual(
                target.querySelectorAll(".o_gantt_row_header.o_gantt_group.o_group_open").length,
                4
            );

            function getConnectorCounts() {
                return target.querySelectorAll(SELECTORS.connector).length;
            }
            function getGroupRow(index) {
                return target.querySelectorAll(".o_gantt_row_header.o_gantt_group")[index];
            }

            assert.strictEqual(getConnectorCounts(), 22);

            await click(getGroupRow(1));
            assert.doesNotHaveClass(getGroupRow(1), "o_group_open");
            assert.strictEqual(getConnectorCounts(), 13);

            await click(getGroupRow(1));
            assert.strictEqual(getConnectorCounts(), 22);

            await click(getGroupRow(1));
            assert.strictEqual(getConnectorCounts(), 13);

            await click(getGroupRow(2));
            assert.strictEqual(getConnectorCounts(), 6);

            await click(getGroupRow(0));
            assert.strictEqual(getConnectorCounts(), 4);

            await click(getGroupRow(3));
            assert.strictEqual(getConnectorCounts(), 0);
        }
    );

    QUnit.test(
        "Connector hovered state is triggered and color is set accordingly.",
        async (assert) => {
            await makeView(ganttViewParams);

            assert.doesNotHaveClass(getConnector(1), CLASSES.highlightedConnector);
            assert.hasAttrValue(
                getConnector(1).querySelector(SELECTORS.connectorStroke),
                "stroke",
                COLORS.default.color
            );

            await triggerEvent(getConnector(1), null, "pointermove");

            assert.hasClass(getConnector(1), CLASSES.highlightedConnector);
            assert.hasAttrValue(
                getConnector(1).querySelector(SELECTORS.connectorStroke),
                "stroke",
                COLORS.default.highlightedColor
            );
        }
    );

    QUnit.test("Buttons are displayed when hovering a connector.", async (assert) => {
        await makeView(ganttViewParams);

        assert.containsNone(
            getConnector(1),
            SELECTORS.connectorStrokeButton,
            "Connectors that are not hovered don't display buttons."
        );

        await triggerEvent(getConnector(1), null, "pointermove");

        assert.containsN(
            getConnector(1),
            SELECTORS.connectorStrokeButton,
            3,
            "Connectors that are hovered display buttons."
        );
    });

    QUnit.test(
        "Buttons are displayed when hovering a connector after a pill has been hovered.",
        async (assert) => {
            await makeView(ganttViewParams);

            assert.containsNone(
                getConnector(1),
                SELECTORS.connectorStrokeButton,
                "Connectors that are not hovered don't display buttons."
            );

            const task1Pill = getPill("Task 1");

            await triggerEvent(task1Pill, null, "pointermove");

            const firstConnector = getConnector(1); // (start at task1Pill)
            assert.containsNone(
                firstConnector,
                SELECTORS.connectorStrokeButton,
                "Connectors that are not hovered don't display buttons."
            );
            assert.hasClass(firstConnector, CLASSES.highlightedConnector);

            await triggerEvent(firstConnector, null, "pointermove");

            assert.hasClass(firstConnector, CLASSES.highlightedConnector);
            assert.containsN(
                getConnector(1),
                SELECTORS.connectorStrokeButton,
                3,
                "Connectors that are hovered display buttons."
            );
        }
    );

    QUnit.test("Connector buttons: remove a dependency", async (assert) => {
        await makeView({
            ...ganttViewParams,
            async mockRPC(_route, { method, model, args }) {
                if (
                    model === "project.task" &&
                    ["web_gantt_reschedule", "write"].includes(method)
                ) {
                    assert.step(JSON.stringify([method, args]));
                    return true;
                }
            },
        });

        await clickConnectorButton(getConnector(1), "remove");

        assert.verifySteps([`["write",[[2],{"depend_on_ids":[[3,1,false]]}]]`]);
    });

    QUnit.test("Connector buttons: reschedule task backward date.", async (assert) => {
        await makeView({
            ...ganttViewParams,
            async mockRPC(_route, { method, model, args }) {
                if (
                    model === "project.task" &&
                    ["web_gantt_reschedule", "write"].includes(method)
                ) {
                    assert.step(JSON.stringify([method, args]));
                    return true;
                }
            },
        });

        await clickConnectorButton(getConnector(1), "reschedule-backward");

        assert.verifySteps([
            `["web_gantt_reschedule",["backward",1,2,"depend_on_ids",null,"planned_date_begin","date_deadline"]]`,
        ]);
    });

    QUnit.test("Connector buttons: reschedule task forward date.", async (assert) => {
        await makeView({
            ...ganttViewParams,
            async mockRPC(_route, { method, model, args }) {
                if (
                    model === "project.task" &&
                    ["web_gantt_reschedule", "write"].includes(method)
                ) {
                    assert.step(JSON.stringify([method, args]));
                    return true;
                }
            },
        });

        await clickConnectorButton(getConnector(1), "reschedule-forward");

        assert.verifySteps([
            `["web_gantt_reschedule",["forward",1,2,"depend_on_ids",null,"planned_date_begin","date_deadline"]]`,
        ]);
    });

    QUnit.test(
        "Connector buttons: reschedule task start backward, different data.",
        async (assert) => {
            await makeView({
                ...ganttViewParams,
                async mockRPC(_route, { method, model, args }) {
                    if (
                        model === "project.task" &&
                        ["web_gantt_reschedule", "write"].includes(method)
                    ) {
                        assert.step(JSON.stringify([method, args]));
                        return true;
                    }
                },
            });

            await clickConnectorButton(getConnector(1), "reschedule-backward");

            assert.verifySteps([
                `["web_gantt_reschedule",["backward",1,2,"depend_on_ids",null,"planned_date_begin","date_deadline"]]`,
            ]);
        }
    );

    QUnit.test("Connector buttons: reschedule task forward, different data.", async (assert) => {
        await makeView({
            ...ganttViewParams,
            async mockRPC(_route, { method, model, args }) {
                if (
                    model === "project.task" &&
                    ["web_gantt_reschedule", "write"].includes(method)
                ) {
                    assert.step(JSON.stringify([method, args]));
                    return true;
                }
            },
        });

        await clickConnectorButton(getConnector(1), "reschedule-forward");

        assert.verifySteps([
            `["web_gantt_reschedule",["forward",1,2,"depend_on_ids",null,"planned_date_begin","date_deadline"]]`,
        ]);
    });

    QUnit.test(
        "Hovering a task pill should highlight related tasks and dependencies",
        async (assert) => {
            assert.expect(31);

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

            ganttViewParams.serverData.models["project.task"].records = [
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

            await makeView(ganttViewParams);

            const connectorMap = getConnectorMap(renderer);
            const pills = [];
            for (const wrapper of target.querySelectorAll(SELECTORS.pillWrapper)) {
                const pillId = wrapper.dataset.pillId;
                pills.push({
                    el: wrapper.querySelector(SELECTORS.pill),
                    recordId: renderer.pills[pillId].record.id,
                });
            }

            const task2Pills = pills.filter((p) => p.recordId === 2);

            assert.strictEqual(task2Pills.length, 2);
            assert.containsNone(target, CLASSES.highlightedPill);

            // Check that all connectors are not in hover state.
            for (const testKey of testMap.keys()) {
                assert.doesNotHaveClass(
                    getConnector(connectorMap.get(testKey).id),
                    CLASSES.highlightedConnector
                );
            }

            await triggerEvent(getPill("Task 2", { nth: 1 }), null, "pointermove");

            // Both pills should be highlighted
            assert.hasClass(getPillWrapper("Task 2", { nth: 1 }), CLASSES.highlightedPill);
            assert.hasClass(getPillWrapper("Task 2", { nth: 2 }), CLASSES.highlightedPill);

            // The rest of the pills should not be highlighted nor display connector creators
            for (const { el, recordId } of pills) {
                if (recordId !== 2) {
                    assert.doesNotHaveClass(el, CLASSES.highlightedPill);
                }
            }

            // Check that all connectors are in the expected hover state.
            for (const [testKey, shouldBeHighlighted] of testMap.entries()) {
                const connector = getConnector(connectorMap.get(testKey).id);
                if (shouldBeHighlighted) {
                    assert.hasClass(connector, CLASSES.highlightedConnector);
                } else {
                    assert.doesNotHaveClass(connector, CLASSES.highlightedConnector);
                }
                assert.containsNone(connector, SELECTORS.connectorStrokeButton);
            }
        }
    );

    QUnit.test(
        "Hovering a connector should cause the connected pills to get highlighted.",
        async (assert) => {
            assert.expect(4);

            await makeView(ganttViewParams);

            assert.containsNone(target, SELECTORS.highlightedConnector);
            assert.containsNone(target, SELECTORS.highlightedPill);

            await triggerEvent(getConnector(1), null, "pointermove");

            assert.containsOnce(target, SELECTORS.highlightedConnector);
            assert.containsN(target, SELECTORS.highlightedPill, 2);
        }
    );

    QUnit.test("Connectors are displayed behind pills, except on hover.", async (assert) => {
        assert.expect(2);

        const getZIndex = (el) => Number(getComputedStyle(el).zIndex) || 0;

        await makeView(ganttViewParams);

        assert.ok(getZIndex(getPillWrapper("Task 2")) > getZIndex(getConnector(1)));

        await triggerEvent(getConnector(1), null, "pointermove");

        assert.ok(getZIndex(getPillWrapper("Task 2")) < getZIndex(getConnector(1)));
    });

    QUnit.test("Create a connector from the gantt view.", async (assert) => {
        assert.expect(2);

        await makeView({
            ...ganttViewParams,
            async mockRPC(_route, { method, model, args }) {
                if (model === "project.task" && method === "write") {
                    assert.step(JSON.stringify([method, args]));
                }
            },
        });

        // Explicitly shows the connector creator wrapper since its "display: none"
        // disappears on native CSS hover, which cannot be programatically emulated.
        const rightWrapper = target.querySelector(SELECTORS.connectorCreatorWrapper);
        rightWrapper.classList.add("d-block");

        await dragAndDrop(
            rightWrapper.querySelector(SELECTORS.connectorCreatorBullet),
            getPill("Task 2")
        );

        assert.verifySteps([`["write",[[2],{"depend_on_ids":[[4,3,false]]}]]`]);
    });

    QUnit.test("Create a connector from the gantt view: going fast", async (assert) => {
        await makeView({
            ...ganttViewParams,
            domain: [["id", "in", [1, 3]]],
        });

        // Explicitly shows the connector creator wrapper since its "display: none"
        // disappears on native CSS hover, which cannot be programatically emulated.
        const rightWrapper = getPillWrapper("Task 1").querySelector(
            SELECTORS.connectorCreatorWrapper
        );
        rightWrapper.classList.add("d-block");

        const connectorBullet = rightWrapper.querySelector(SELECTORS.connectorCreatorBullet);
        const bulletRect = connectorBullet.getBoundingClientRect();
        const initialPosition = {
            x: Math.floor(bulletRect.left), // floor to avoid sub-pixel positioning
            y: Math.floor(bulletRect.top), // floor to avoid sub-pixel positioning
        };
        await triggerEvent(connectorBullet, null, "pointerdown", {
            clientX: initialPosition.x,
            clientY: initialPosition.y,
        });

        // Here we simulate a fast move, using arbitrary values.
        const currentPosition = {
            x: Math.floor(initialPosition.x + 123), // floor to avoid sub-pixel positioning
            y: Math.floor(initialPosition.y + 12), // floor to avoid sub-pixel positioning
        };
        await triggerEvent(target, null, "pointermove", {
            clientX: currentPosition.x,
            clientY: currentPosition.y,
        });

        // Then we check that the connector stroke is correctly positioned.
        const connectorStroke = getConnector("new").querySelector(SELECTORS.connectorStroke);
        const strokeRect = connectorStroke.getBoundingClientRect();
        assert.strictEqual(strokeRect.left, initialPosition.x);
        assert.strictEqual(strokeRect.top, initialPosition.y);
        assert.strictEqual(strokeRect.left + strokeRect.width, currentPosition.x);
        assert.strictEqual(strokeRect.top + strokeRect.height, currentPosition.y);
    });

    QUnit.test("Connectors should be rendered if connected pill is not visible", async (assert) => {
        // Generate a lot of users so that the connectors are far beyond the visible
        // viewport, hence generating fake extra pills to render the connectors.
        for (let i = 0; i < 100; i++) {
            const id = 100 + i;
            ganttViewParams.serverData.models["res.users"].records.push({
                id,
                name: `User ${id}`,
            });
            ganttViewParams.serverData.models["project.task"].records.push({
                id,
                name: `Task ${id}`,
                planned_date_begin: "2021-10-11 18:30:00",
                date_deadline: "2021-10-11 19:29:59",
                user_ids: [id],
                depend_on_ids: [],
            });
        }
        ganttViewParams.serverData.models["project.task"].records[12].user_ids = [199];

        await makeView(ganttViewParams);

        assert.containsN(target, SELECTORS.connector, 13);
    });

    QUnit.test("No display of resize handles when creating a connector", async (assert) => {
        assert.expect(1);
        await makeView(ganttViewParams);

        // Explicitly shows the connector creator wrapper since its "display: none"
        // disappears on native CSS hover, which cannot be programatically emulated.
        const rightWrapper = target.querySelector(SELECTORS.connectorCreatorWrapper);
        rightWrapper.classList.add("d-block");

        // Creating a connector and hover another pill while dragging it
        const { moveTo } = await drag(rightWrapper.querySelector(SELECTORS.connectorCreatorBullet));
        await moveTo(getPill("Task 2"));
        assert.containsNone(target, SELECTORS.resizeHandle);
    });

    QUnit.test("Renderer in connect mode when creating a connector", async (assert) => {
        await makeView(ganttViewParams);

        // Explicitly shows the connector creator wrapper since its "display: none"
        // disappears on native CSS hover, which cannot be programatically emulated.
        const rightWrapper = target.querySelector(SELECTORS.connectorCreatorWrapper);
        rightWrapper.classList.add("d-block");

        // Creating a connector and hover another pill while dragging it
        const { moveTo } = await drag(rightWrapper.querySelector(SELECTORS.connectorCreatorBullet));
        await moveTo(getPill("Task 2"));
        assert.hasClass(target.querySelector(SELECTORS.renderer), "o_connect");
    });

    QUnit.test(
        "Connector creators of initial pill are highlighted when creating a connector",
        async (assert) => {
            await makeView(ganttViewParams);

            // Explicitly shows the connector creator wrapper since its "display: none"
            // disappears on native CSS hover, which cannot be programatically emulated.
            const sourceWrapper = target.querySelector(SELECTORS.pillWrapper);
            const rightWrapper = sourceWrapper.querySelector(SELECTORS.connectorCreatorWrapper);
            rightWrapper.classList.add("d-block");

            // Creating a connector and hover another pill while dragging it
            const { moveTo } = await drag(
                rightWrapper.querySelector(SELECTORS.connectorCreatorBullet)
            );
            await moveTo(getPill("Task 2"));
            assert.hasClass(sourceWrapper, CLASSES.lockedConnectorCreator);
        }
    );

    QUnit.test(
        "Connector creators of hovered pill are highlighted when creating a connector",
        async (assert) => {
            await makeView(ganttViewParams);

            // Explicitly shows the connector creator wrapper since its "display: none"
            // disappears on native CSS hover, which cannot be programatically emulated.
            const rightWrapper = target.querySelector(SELECTORS.connectorCreatorWrapper);
            rightWrapper.classList.add("d-block");

            // Creating a connector and hover another pill while dragging it
            const { moveTo } = await drag(
                rightWrapper.querySelector(SELECTORS.connectorCreatorBullet)
            );

            const destinationWrapper = getPillWrapper("Task 2");
            const destinationPill = destinationWrapper.querySelector(SELECTORS.pill);
            await moveTo(destinationPill);

            // moveTo only triggers a pointerenter event on destination pill,
            // a pointermove event is still needed to highlight it
            await triggerEvent(destinationPill, null, "pointermove");
            assert.hasClass(destinationWrapper, CLASSES.highlightedConnectorCreator);
        }
    );

    QUnit.test(
        "Switch to full-size browser: the connections between pills should be diplayed",
        async (assert) => {
            const ui = { isSmall: true };
            patchWithCleanup(browser, { setTimeout: (fn) => fn() });
            const fakeUIService = {
                start(env) {
                    Object.defineProperty(env, "isSmall", {
                        get() {
                            return ui.isSmall;
                        },
                    });
                    return ui;
                },
            };
            registry.category("services").add("ui", fakeUIService);
            await makeView(ganttViewParams);

            // Mobile view
            assert.containsNone(
                target,
                "svg.o_gantt_connector",
                "Gantt connectors should not be visible in small/mobile view"
            );

            // Resizing browser to leave mobile view
            ui.isSmall = false;
            patchWithCleanup(browser, { innerWidth: 1200 });
            await triggerEvent(window, null, "resize");
            assert.containsN(
                target,
                "svg.o_gantt_connector",
                22,
                "Gantt connectors should be visible when switching to desktop view"
            );
        }
    );
});
