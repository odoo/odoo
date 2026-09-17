// @ts-check

import { after, before, describe, expect, test } from "@odoo/hoot";
import { Deferred, runAllTimers, tick } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    disableLogging,
    enableLogging,
    getStatus,
    makeLogger,
} from "@web/core/debug/debug_logger";
import { useProgressBar } from "@web/views/kanban/progress_bar_hook";

describe.current.tags("desktop");
const log = makeLogger("web.kanban.progress.lifecycle");
before(() => {
    const previous = getStatus().spec;
    enableLogging("web.kanban.progress.lifecycle", { persist: false });
    after(() =>
        previous
            ? enableLogging(previous, { persist: false })
            : disableLogging({ persist: false }),
    );
});

const COLORS = { done: "success", blocked: "danger" };

/** @param {Record<string, any>} [opts] */
function makeGroup({ id = "g1", value = "a", count = 3, records = [] } = {}) {
    return {
        id,
        value,
        serverValue: value,
        count,
        aggregates: {},
        groupDomain: [["stage", "=", value]],
        list: { count: records.length || count, records },
    };
}

/** @param {Record<string, any>} [opts] */
function makeModel({ groups = [makeGroup()], readProgressBar } = {}) {
    /** @type {Record<string, Function[]>} */
    const hooks = {};
    /** @type {any[]} */
    const calls = [];
    return {
        calls,
        isReady: true,
        root: {
            groups,
            groupByField: { name: "stage" },
            fields: { state: {} },
            context: {},
            domain: /** @type {any[]} */ ([]),
            groupBy: ["stage"],
            resModel: "task",
        },
        orm: {
            call: (
                /** @type {any} */ resModel,
                /** @type {any} */ method,
                /** @type {any} */ args,
                /** @type {any} */ kwargs,
            ) => {
                calls.push(method);
                return readProgressBar
                    ? readProgressBar(kwargs)
                    : Promise.resolve({ a: { done: 2, blocked: 0 } });
            },
            formattedReadGroup: () => Promise.resolve([]),
        },
        subscribeLifecycle(/** @type {any} */ name, /** @type {any} */ cb) {
            (hooks[name] ||= []).push(cb);
            return () => {
                hooks[name].splice(hooks[name].indexOf(cb), 1);
            };
        },
        async fire(/** @type {any} */ name, /** @type {any[]} */ ...args) {
            for (const cb of hooks[name] || []) {
                await cb(...args);
            }
        },
    };
}

/** @param {Record<string, any>} [opts] */
async function mountProgressBar({
    model = makeModel(),
    aggregateFields = [],
    activeBars = {},
} = {}) {
    /** @type {any} */
    let state = null;
    class Host extends Component {
        static template = xml`<div/>`;
        static props = {};
        setup() {
            state = useProgressBar(
                { fieldName: "state", colors: COLORS, help: "" },
                model,
                aggregateFields,
                activeBars,
            );
        }
    }
    const host = await mountWithCleanup(Host);
    return { state, model, destroy: () => host.__owl__.app.destroy() };
}

async function load(/** @type {any} */ model) {
    await model.fire("onWillLoadRoot", {
        context: {},
        domain: [],
        groupBy: ["stage"],
        resModel: "task",
    });
    await model.fire("onRootLoaded");
}

describe("destruction while requests are pending", () => {
    test("a settled request cannot publish while its continuation is queued at destruction", async () => {
        const response = Promise.withResolvers();
        const model = makeModel({ readProgressBar: () => response.promise });
        const { state, destroy } = await mountProgressBar({ model });
        const pending = state.loadProgressBar(model.root);
        response.resolve({ a: { done: 99 } });
        await Promise.resolve();
        log.logic("settled before destruction", () => ({
            guardPending: state._pbLoads._rejectPending !== null,
            counts: state._pbCounts,
        }));
        destroy();
        await pending;
        expect(state._pbCounts).toBe(null);
    });

    test("destruction releases all pending guards and consumes late failures", async () => {
        let aborts = 0;
        let completed = 0;
        const requests = Array.from({ length: 3 }, () =>
            Object.assign(new Deferred(), {
                abort: () => aborts++,
            }),
        );
        const model = makeModel({ readProgressBar: () => requests[0] });
        const { state, destroy } = await mountProgressBar({ model });
        let aggregateRequest = 1;
        model.orm.formattedReadGroup = () => requests[aggregateRequest++];
        const pending = [
            state.loadProgressBar(model.root),
            state._updateAggregates(),
            state._updateAggregateGroup(model.root.groups[0], [], { value: "done" }),
        ].map((promise) => promise.then(() => completed++));
        destroy();
        await tick();
        log.logic("pending work cancelled", () => ({ aborts, completed }));
        expect(aborts).toBe(3);
        expect(completed).toBe(3);
        for (const request of requests) {
            request.reject(new Error("late transport failure"));
        }
        await Promise.all(pending);
        await tick();
        expect(state._pbCounts).toBe(null);
    });

    test("a late counts response cannot schedule another request", async () => {
        const model = makeModel();
        const { state, destroy } = await mountProgressBar({ model });
        await load(model);
        const before = state._pbCounts;
        const late = new Deferred();
        model.orm.call = () => {
            model.calls.push("late counts");
            return late;
        };
        const pending = state._updateProgressBar();
        model.root.groups.push(makeGroup({ id: "g2", value: "b" }));
        destroy();
        const callsAtDestroy = model.calls.length;
        late.resolve({ a: { done: 99 } });
        await pending;
        await runAllTimers();
        log.logic("counts after destroy", () => ({
            callsAtDestroy,
            calls: model.calls.length,
        }));
        expect(model.calls.length).toBe(callsAtDestroy);
        expect(state._pbCounts).toBe(before);
    });

    test("an awaiting root callback cannot deselect a bar after destruction", async () => {
        const late = new Deferred();
        const model = makeModel({ readProgressBar: () => late });
        const group = model.root.groups[0];
        let filters = 0;
        Object.assign(group, {
            applyFilter: async () => filters++,
            model: { notify() {} },
        });
        const { state, destroy } = await mountProgressBar({
            model,
            activeBars: { '"a"': { value: "done", count: 2 } },
        });
        // A root reload may still have counts from the previous root.
        state._pbCounts = { a: { done: 0 } };
        const previousCounts = state._pbCounts;
        const pending = load(model);
        await tick();
        destroy();
        late.resolve({ a: { done: 0 } });
        await pending;
        await tick();
        log.logic("root continuation after destroy", () => ({ filters }));
        expect(filters).toBe(0);
        expect(state._pbCounts).toBe(previousCounts);
    });

    for (const value of ["done", null]) {
        test(`a pending bar selection (${value}) cannot refresh or notify after destruction`, async () => {
            const model = makeModel({
                readProgressBar: () => Promise.resolve({ a: { done: 2, blocked: 1 } }),
            });
            const late = new Deferred();
            let notifications = 0;
            Object.assign(model.root.groups[0], {
                applyFilter: () => late,
                model: { notify: () => notifications++ },
            });
            const activeBars = { '"a"': { value: "blocked", count: 1 } };
            const { state, destroy } = await mountProgressBar({ model, activeBars });
            await load(model);
            const previous = { ...state.activeBars };
            const pending = state.selectBar("g1", { value });
            destroy();
            const callsAtDestroy = model.calls.length;
            late.resolve();
            await pending;
            await tick();
            log.logic("selection after destroy", () => ({
                notifications,
                calls: model.calls.length,
                callsAtDestroy,
            }));
            expect(model.calls.length).toBe(callsAtDestroy);
            expect(notifications).toBe(0);
            expect(state.activeBars).toEqual(previous);
        });
    }

    test("pending aggregate responses cannot mutate retained state after destruction", async () => {
        const model = makeModel();
        Object.assign(model.root.fields, {
            stage: { type: "char" },
            amount: { type: "float", aggregator: "sum" },
        });
        const { state, destroy } = await mountProgressBar({ model });
        await load(model);
        const late = new Deferred();
        model.orm.formattedReadGroup = () => late;
        const previous = state._aggregatesByKey;
        const activeBar = { value: "done", aggregates: { amount: 7 } };
        const all = state._updateAggregates();
        const one = state._updateAggregateGroup(model.root.groups[0], [], activeBar);
        destroy();
        late.resolve([{ stage: "a", amount: 99, __count: 3 }]);
        await Promise.all([all, one]);
        log.logic("aggregate responses after destroy", () => ({
            retained: state._aggregatesByKey === previous,
        }));
        expect(state._aggregatesByKey).toBe(previous);
        expect(activeBar.aggregates).toEqual({ amount: 7 });
    });
});

describe("seeding a group from the fetched counts", () => {
    test("bars come from the colors, plus an Other bar that absorbs the remainder", async () => {
        const model = makeModel({ groups: [makeGroup({ count: 5 })] });
        const { state } = await mountProgressBar({ model });
        await load(model);

        const info = state.getGroupInfo(model.root.groups[0]);
        expect(info.bars.map((/** @type {any} */ b) => b.value.toString())).toEqual([
            "done",
            "blocked",
            "Symbol(False)",
        ]);
        expect(info.bars.map((/** @type {any} */ b) => b.count)).toEqual([2, 0, 3], {
            message: "Other is group.count minus the coloured counts",
        });
        expect(info.total).toBe(5);
        expect(info.isReady).toBe(true);
    });

    test("a group the fetch says nothing about seeds every bar at zero", async () => {
        const model = makeModel({
            groups: [makeGroup({ id: "g2", value: "z", count: 4 })],
        });
        const { state } = await mountProgressBar({ model });
        await load(model);

        const info = state.getGroupInfo(model.root.groups[0]);
        expect(info.bars.map((/** @type {any} */ b) => b.count)).toEqual([0, 0, 4]);
        expect(info.total).toBe(4);
    });
});

describe("the epoch guard on the counts fetch", () => {
    test("a superseded response is discarded, and the last one wins", async () => {
        const first = new Deferred();
        const second = new Deferred();
        const pending = [first, second];
        const model = makeModel({
            groups: [makeGroup({ count: 5 })],
            readProgressBar: () => pending.shift() ?? Promise.resolve({}),
        });
        const { state } = await mountProgressBar({ model });
        pending.unshift(
            /** @type {any} */ (Promise.resolve({ a: { done: 2, blocked: 0 } })),
        );
        await load(model);

        state.updateCounts(model.root.groups[0], null);
        state.updateCounts(model.root.groups[0], null);

        second.resolve({ a: { done: 4, blocked: 1 } });
        await tick();
        await tick();
        first.resolve({ a: { done: 99, blocked: 99 } });
        await tick();
        await tick();
        await runAllTimers();

        const info = state.getGroupInfo(model.root.groups[0]);
        expect(info.bars.map((/** @type {any} */ b) => b.count)).toEqual([4, 1, 0], {
            message: "the stale response never landed",
        });
    });
});

describe("group membership changing under a fetch", () => {
    test("counts are not applied when the groups changed, and a retry is scheduled", async () => {
        const groups = [makeGroup({ id: "g1", count: 5 })];
        const answer = new Deferred();
        const model = makeModel({
            groups,
            readProgressBar: () => answer,
        });
        const { state } = await mountProgressBar({ model });
        answer.resolve({ a: { done: 2, blocked: 0 } });
        await load(model);
        const before = state
            .getGroupInfo(groups[0])
            .bars.map((/** @type {any} */ b) => b.count);

        const late = new Deferred();
        model.orm.call = () => {
            model.calls.push("read_progress_bar");
            return late;
        };
        state.updateCounts(groups[0], null);
        groups.push(makeGroup({ id: "g2", value: "b", count: 1 }));
        late.resolve({ a: { done: 99, blocked: 99 }, b: { done: 1, blocked: 0 } });
        await tick();
        await tick();

        expect(
            state.getGroupInfo(groups[0]).bars.map((/** @type {any} */ b) => b.count),
        ).toEqual(before, {
            message:
                "the answer described a different set of groups, so it was dropped",
        });

        const callsBefore = model.calls.length;
        await runAllTimers();
        expect(model.calls.length > callsBefore).toBe(true, {
            message: "and the retry the guard scheduled did fire",
        });
    });
});

describe("optimistic accounting for a record move", () => {
    /** @returns {Promise<any>} */
    async function twoGroups() {
        const record = { id: "r1", data: { state: "done" } };
        const source = makeGroup({ id: "g1", value: "a", count: 3, records: [record] });
        const target = makeGroup({ id: "g2", value: "b", count: 1 });
        const model = makeModel({
            groups: [source, target],
            readProgressBar: () =>
                Promise.resolve({
                    a: { done: 2, blocked: 0 },
                    b: { done: 0, blocked: 1 },
                }),
        });
        const { state } = await mountProgressBar({ model });
        await load(model);
        return { state, model, source, target, record };
    }

    test("a registered move shifts one unit from source to target without refetching", async () => {
        const { state, model, source, target, record } = await twoGroups();
        const callsBefore = model.calls.length;

        state.registerRecordMove("r1", "g1", "g2");
        state.updateCounts(target, record);

        expect(state.getGroupInfo(source).bars[0].count).toBe(1, {
            message: "source lost the unit it held for that value",
        });
        expect(state.getGroupInfo(target).bars[0].count).toBe(1, {
            message: "target gained it",
        });
        expect(model.calls.length).toBe(callsBefore, {
            message: "and nothing was refetched to learn that",
        });
    });

    test("the reconcile fetch follows, once, after the debounce", async () => {
        const { state, model, target, record } = await twoGroups();
        const callsBefore = model.calls.length;

        state.registerRecordMove("r1", "g1", "g2");
        state.updateCounts(target, record);
        expect(model.calls.length).toBe(callsBefore);

        await runAllTimers();
        expect(model.calls.length).toBe(callsBefore + 1, {
            message:
                "the optimistic delta is confirmed against the server exactly once",
        });
    });

    test("registering the same record twice keeps the first move", async () => {
        const { state, source, target, record } = await twoGroups();

        state.registerRecordMove("r1", "g1", "g2");
        state.registerRecordMove("r1", "g2", "g1");
        state.updateCounts(target, record);

        expect(state.getGroupInfo(source).bars[0].count).toBe(1);
        expect(state.getGroupInfo(target).bars[0].count).toBe(1);
    });

    test("a cancelled move takes the ordinary refetch path instead", async () => {
        const { state, model, source, target, record } = await twoGroups();
        const callsBefore = model.calls.length;

        state.registerRecordMove("r1", "g1", "g2");
        state.cancelRecordMove("r1");
        state.updateCounts(target, record);

        expect(state.getGroupInfo(source).bars[0].count).toBe(2, {
            message: "no optimistic delta was applied",
        });
        expect(model.calls.length).toBe(callsBefore + 1, {
            message: "the counts were refetched instead",
        });
    });

    test("a move on the field the view is grouped by is left to the refetch", async () => {
        const { state, model, source, target, record } = await twoGroups();
        model.root.groupByField = { name: "state" };
        const callsBefore = model.calls.length;

        state.registerRecordMove("r1", "g1", "g2");
        state.updateCounts(target, record);

        expect(state.getGroupInfo(source).bars[0].count).toBe(2);
        expect(model.calls.length).toBe(callsBefore + 1);
    });
});

describe("dropping the group-by", () => {
    test("counts from the grouped load do not survive into an ungrouped root", async () => {
        const model = makeModel();
        const { state } = await mountProgressBar({ model });
        await load(model);
        expect(state._pbCounts).not.toBe(null);

        // The user removes the group-by: the root becomes a record list, which
        // has no `groups` at all.
        delete model.root.groups;
        model.root.groupBy = [];
        const callsBefore = model.calls.length;
        await model.fire("onWillLoadRoot", {
            context: {},
            domain: [],
            groupBy: [],
            resModel: "task",
        });
        await model.fire("onRootLoaded");

        expect(state._pbCounts).toBe(null, {
            message: "the stale grouped counts were dropped",
        });
        expect(model.calls.length).toBe(callsBefore, {
            message: "no counts are fetched without a group-by",
        });
    });

    test("refreshing the bars on an ungrouped root is a no-op", async () => {
        const model = makeModel();
        const { state } = await mountProgressBar({ model });
        await load(model);

        delete model.root.groups;
        model.root.groupBy = [];

        expect(() => state._refreshBars()).not.toThrow();
        expect(() => state._deselectActiveBars(() => true)).not.toThrow();
    });
});
