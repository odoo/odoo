import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { Deferred, animationFrame, mockDate } from "@odoo/hoot-mock";
import { click } from "@odoo/hoot-dom";
import { onPatched } from "@odoo/owl";
import {
    onRpc,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { Tasks, defineGanttModels } from "./gantt_mock_models";
import {
    SELECTORS,
    editPill,
    ganttControlsChanges,
    getActiveScale,
    getCellColorProperties,
    getGridContent,
    getPillWrapper,
    mountGanttView,
    resizePill,
    selectGanttRange,
    setScale,
} from "./web_gantt_test_helpers";

describe.current.tags("desktop");

defineGanttModels();
beforeEach(() => mockDate("2018-12-20T08:00:00", +1));

test("concurrent scale switches return in inverse order", async () => {
    let model;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            model = this.model;
            onPatched(() => {
                expect.step("patched");
            });
        },
    });

    let firstReloadProm = null;
    let reloadProm = null;
    onRpc("get_gantt_data", () => reloadProm);
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
    });
    expect.verifySteps(["patched"]);

    let content = getGridContent();
    expect(getActiveScale()).toBe(2);
    expect(content.groupHeaders.map((gh) => gh.title)).toEqual(["December 2018", "January 2019"]);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    expect(model.data.records).toHaveLength(6);

    // switch to 'week' scale (this rpc will be delayed)
    firstReloadProm = new Deferred();
    reloadProm = firstReloadProm;
    await setScale(4);
    await ganttControlsChanges();

    content = getGridContent();
    expect(getActiveScale()).toBe(4);
    expect(content.groupHeaders.map((gh) => gh.title)).toEqual(["December 2018", "January 2019"]);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    expect(model.data.records).toHaveLength(6);

    // switch to 'year' scale
    reloadProm = null;
    await setScale(0);
    await ganttControlsChanges();

    content = getGridContent();
    expect(getActiveScale()).toBe(0);
    expect(content.groupHeaders.map((gh) => gh.title)).toEqual(["2018", "2019"]);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    expect(model.data.records).toHaveLength(6);

    firstReloadProm.resolve();
    await animationFrame();

    content = getGridContent();
    expect(getActiveScale()).toBe(0);
    expect(content.groupHeaders.map((gh) => gh.title)).toEqual(["2018", "2019"]);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    expect(model.data.records).toHaveLength(6);
    expect.verifySteps(["patched"]);
});

test("concurrent scale switches return with gantt unavailabilities", async () => {
    const unavailabilities = [
        [{ start: "2018-12-10 23:00:00", stop: "2018-12-11 23:00:00" }],
        [{ start: "2018-12-10 23:00:00", stop: "2018-12-11 23:00:00" }],
        [
            { start: "2018-07-30 23:00:00", stop: "2018-08-31 23:00:00" },
            { start: "2018-12-10 23:00:00", stop: "2018-12-11 23:00:00" },
        ],
        [{ start: "2018-07-30 23:00:00", stop: "2018-08-31 23:00:00" }],
    ];

    let model;
    patchWithCleanup(GanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            model = this.model;
            onPatched(() => {
                expect.step("patched");
            });
        },
    });

    let firstReloadProm = null;
    let reloadProm = null;
    onRpc("get_gantt_data", async ({ parent }) => {
        const result = parent();
        result.unavailabilities.__default = { false: unavailabilities.shift() };
        await reloadProm;
        return result;
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" display_unavailability="true"/>`,
    });
    expect.verifySteps(["patched"]);

    let content = getGridContent();
    expect(getActiveScale()).toBe(2);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    expect(content.groupHeaders.map((h) => h.title)).toEqual(["December 2018", "January 2019"]);
    expect(model.data.records).toHaveLength(6);
    expect(getCellColorProperties("08 December 2018")).toEqual([]);
    expect(getCellColorProperties("11 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
    ]);

    // switch to 'week' scale (this rpc will be delayed)
    firstReloadProm = new Deferred();
    reloadProm = firstReloadProm;
    await setScale(4);
    await ganttControlsChanges();

    content = getGridContent();
    expect(getActiveScale()).toBe(4);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    expect(content.groupHeaders.map((h) => h.title)).toEqual(["December 2018", "January 2019"]);
    expect(model.data.records).toHaveLength(6);
    expect(getCellColorProperties("08 December 2018")).toEqual([]);
    expect(getCellColorProperties("11 December 2018")).toEqual([
        "--Gantt__DayOff-background-color",
    ]);

    // switch to 'year' scale
    reloadProm = null;
    await setScale(0);
    await ganttControlsChanges();
    expect.verifySteps(["patched"]);
    await selectGanttRange({ startDate: "2018-01-01", stopDate: "2018-12-31" });
    expect.verifySteps(["patched"]);

    content = getGridContent();
    expect(getActiveScale()).toBe(0);
    expect(content.range).toBe("01/01/2018 -> 12/31/2018");
    expect(content.groupHeaders.map((h) => h.title)).toEqual(["2018"]);
    expect(model.data.records).toHaveLength(7);
    expect(getCellColorProperties("August 2018")).toEqual(["--Gantt__DayOff-background-color"]);
    expect(getCellColorProperties("November 2018")).toEqual([]);

    firstReloadProm.resolve();
    await animationFrame();

    content = getGridContent();
    expect(getActiveScale()).toBe(0);
    expect(content.range).toBe("01/01/2018 -> 12/31/2018");
    expect(content.groupHeaders.map((h) => h.title)).toEqual(["2018"]);
    expect(model.data.records).toHaveLength(7);
    expect(getCellColorProperties("August 2018")).toEqual(["--Gantt__DayOff-background-color"]);
    expect(getCellColorProperties("November 2018")).toEqual([]);
    expect.verifySteps([]);
});

test("concurrent range selections", async () => {
    let reloadProm = null;
    let firstReloadProm = null;
    onRpc("get_gantt_data", () => reloadProm);
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
    });

    let content = getGridContent();
    expect(getActiveScale()).toBe(2);
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");

    reloadProm = new Deferred();
    firstReloadProm = reloadProm;
    await selectGanttRange({ startDate: "2019-01-01", stopDate: "2019-02-28" });
    reloadProm = null;
    await selectGanttRange({ startDate: "2019-01-01", stopDate: "2019-01-31" });
    firstReloadProm.resolve();
    content = getGridContent();
    expect(content.range).toBe("01/01/2019 -> 01/31/2019");
});

test("concurrent pill resize and groupBy change", async () => {
    let awaitWriteDef = false;
    const writeDef = new Deferred();
    onRpc(({ args, method }) => {
        expect.step([method, args]);
        if (method === "write" && awaitWriteDef) {
            return writeDef;
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        searchViewArch: `
            <search>
                <filter name="group_by" string="Project" domain="[]" context="{ 'group_by': 'project_id' }"/>
            </search>
        `,
        domain: [["id", "in", [2, 5]]],
    });
    expect.verifySteps([
        ["get_views", []],
        ["get_gantt_data", []],
    ]);
    expect(getGridContent().rows).toEqual([
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                    level: 0,
                    title: "Task 5",
                },
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
        },
    ]);

    // resize "Task 2" to 1 cell smaller (-1 day) ; this RPC will be delayed
    awaitWriteDef = true;
    await resizePill(getPillWrapper("Task 2"), "end", -1);

    expect.verifySteps([["write", [[2], { stop: "2018-12-21 06:29:59" }]]]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Project");
    expect.verifySteps([["get_gantt_data", []]]);
    expect(getGridContent().rows).toEqual([
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Project 1",
        },
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                    level: 0,
                    title: "Task 5",
                },
            ],
            title: "Project 2",
        },
    ]);

    writeDef.resolve();
    await animationFrame();
    expect.verifySteps([["get_gantt_data", []]]);
    expect(getGridContent().rows).toEqual([
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 21 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Project 1",
        },
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 04 (1/2) December 2018",
                    level: 0,
                    title: "Task 5",
                },
            ],
            title: "Project 2",
        },
    ]);
});

test("concurrent pill resizes return in inverse order", async () => {
    let awaitWriteDef = false;
    const writeDef = new Deferred();
    onRpc(({ args, method }) => {
        expect.step([method, args]);
        if (method === "write" && awaitWriteDef) {
            return writeDef;
        }
    });
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        domain: [["id", "=", 2]],
    });

    // resize to 1 cell smaller (-1 day) ; this RPC will be delayed
    awaitWriteDef = true;
    await resizePill(getPillWrapper("Task 2"), "end", -1);

    // resize to two cells larger (+2 days) ; no delay
    awaitWriteDef = false;
    await resizePill(getPillWrapper("Task 2"), "end", +2);

    writeDef.resolve();
    await animationFrame();

    expect.verifySteps([
        ["get_views", []],
        ["get_gantt_data", []],
        ["write", [[2], { stop: "2018-12-21 06:29:59" }]],
        ["get_gantt_data", []],
        ["write", [[2], { stop: "2018-12-24 06:29:59" }]],
        ["get_gantt_data", []],
    ]);
});

test("concurrent pill resizes and open, dialog show updated number", async () => {
    Tasks._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
            </form>
        `,
    };

    const def = new Deferred();
    onRpc("write", () => def);
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        domain: [["id", "=", 2]],
    });

    await resizePill(getPillWrapper("Task 2"), "end", +2);
    await editPill("Task 2");

    def.resolve();
    await animationFrame();
    expect(`.modal [name=stop] input`).toHaveValue("12/24/2018 07:29:59");
});

test("concurrent display mode change and fetch", async () => {
    let def;
    onRpc("get_gantt_data", () => def);
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop"/>`,
        domain: [["id", "in", [1, 2]]],
    });

    let content = getGridContent();
    expect(content.range).toBe("12/01/2018 -> 02/28/2019");
    const initialRows = [
        {
            pills: [
                { title: "Task 1", level: 0, colSpan: "Out of bounds (1)  -> 31 December 2018" },
                {
                    title: "Task 2",
                    level: 1,
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                },
            ],
        },
    ];
    expect(content.rows).toEqual(initialRows);

    def = new Deferred();
    await selectGanttRange({ startDate: "2018-12-01", stopDate: "2019-06-15" });
    content = getGridContent();
    expect(content.range).toBe("12/01/2018 -> 06/15/2019");
    expect(content.rows).toEqual(initialRows);

    await click(SELECTORS.sparse);
    await animationFrame();
    content = getGridContent();
    expect(content.range).toBe("12/01/2018 -> 06/15/2019");
    expect(content.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 0,
                    title: "Task 1",
                },
            ],
            title: "Task 1",
        },
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Task 2",
        },
    ]);

    def.resolve();
    await animationFrame();
    content = getGridContent();
    expect(content.range).toBe("12/01/2018 -> 06/15/2019");
    expect(content.rows).toEqual([
        {
            pills: [
                {
                    colSpan: "Out of bounds (1)  -> 31 December 2018",
                    level: 0,
                    title: "Task 1",
                },
            ],
            title: "Task 1",
        },
        {
            pills: [
                {
                    colSpan: "17 (1/2) December 2018 -> 22 (1/2) December 2018",
                    level: 0,
                    title: "Task 2",
                },
            ],
            title: "Task 2",
        },
    ]);
});
