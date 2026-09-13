// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeLogger } from "@web/core/debug/debug_logger";
import { makeActiveField } from "@web/model/relational_model/field_metadata";
import { StaticList } from "@web/model/relational_model/static_list";
import { sortBy, sortStaticList } from "@web/model/relational_model/static_list_sort";

import { makeTestRelationalModel } from "./model_test_helpers.js";

describe.current.tags("headless");

/**
 * @param {[number, {resId: number, data: Record<string, unknown>, virtualId?: null}][]} entries
 */
function makeCache(entries) {
    return new Map(
        entries.map(([id, record]) => [
            id,
            {
                ...record,
                applyValues(values) {
                    Object.assign(this.data, values);
                },
            },
        ]),
    );
}

/** @param {Partial<import("@web/model/relational_model/static_list_sort").SortableList>} [overrides] */
function makeList(overrides = {}) {
    const loadCalls = [];
    /** @type {import("@web/model/relational_model/static_list_sort").SortableList & {_loadCalls: Parameters<import("@web/model/relational_model/static_list").StaticList["loadLocked"]>[0][]}} */
    const list = {
        currentIds: [],
        _currentIds: [],
        orderBy: [],
        _needsReordering: false,
        activeFields: {},
        fields: {},
        fieldNames: [],
        evalContext: {},
        config: {
            resModel: "res.partner",
            fields: {},
            activeFields: {},
            fieldsToAggregate: [],
            isMonoRecord: false,
            isRoot: false,
            context: {},
            domain: [],
            groupBy: [],
            orderBy: [],
        },
        _cache: new Map(),
        _getResIdsToLoad: () => [],
        loadLocked: async (params) => {
            loadCalls.push(params);
        },
        markReordered() {
            this._needsReordering = false;
        },
        _createRecordDatapoint: () => {},
        model: {
            loadRecords: async () => [],
        },
        _loadCalls: loadCalls,
        ...overrides,
    };
    return list;
}

describe("sort — empty orderBy", () => {
    test("returns currentIds unchanged when orderBy is empty", async () => {
        const list = makeList();
        const ids = [3, 1, 2];
        const result = await sortStaticList(list, ids, []);
        expect(result).toBe(ids);
    });

    test("does not call list.loadLocked when orderBy is empty", async () => {
        const list = makeList();
        await sortStaticList(list, [1, 2], []);
        expect(list._loadCalls.length).toBe(0);
    });

    test("uses list.orderBy default when not provided", async () => {
        const list = makeList({ orderBy: [] });
        const ids = [5, 6];
        const result = await sortStaticList(list, ids);
        expect(result).toBe(ids);
    });
});

describe("sort — with cached records", () => {
    test("sorts records by field and calls loadLocked with sorted IDs", async () => {
        const list = makeList({
            fields: { name: { name: "name", type: "char" } },
        });
        list._cache = makeCache([
            [1, { resId: 1, virtualId: null, data: { name: "Zebra" } }],
            [2, { resId: 2, virtualId: null, data: { name: "Apple" } }],
            [3, { resId: 3, virtualId: null, data: { name: "Mango" } }],
        ]);

        await sortStaticList(list, [1, 2, 3], [{ name: "name", asc: true }]);

        expect(list._loadCalls.length).toBe(1);
        expect(list._loadCalls[0].nextCurrentIds).toEqual([2, 3, 1]);
    });

    test("clears _needsReordering flag after sort", async () => {
        const list = makeList({
            fields: { name: { name: "name", type: "char" } },
            _needsReordering: true,
        });
        list._cache = makeCache([[1, { resId: 1, data: { name: "A" } }]]);

        await sortStaticList(list, [1], [{ name: "name", asc: true }]);

        expect(list._needsReordering).toBe(false);
    });

    test("descending sort reverses the order", async () => {
        const list = makeList({
            fields: { name: { name: "name", type: "char" } },
        });
        list._cache = makeCache([
            [1, { resId: 1, data: { name: "Apple" } }],
            [2, { resId: 2, data: { name: "Zebra" } }],
        ]);

        await sortStaticList(list, [1, 2], [{ name: "name", asc: false }]);

        expect(list._loadCalls[0].nextCurrentIds).toEqual([2, 1]);
    });
});

describe("sortBy — direction cycling", () => {
    test("new field sorts ascending", async () => {
        const list = makeList({
            orderBy: [],
            fields: { name: { name: "name", type: "char" } },
            _cache: makeCache([[1, { resId: 1, data: { name: "A" } }]]),
        });

        await sortBy(list, "name");

        expect(list._loadCalls.length).toBe(1);
        expect(list._loadCalls[0].orderBy).toEqual([{ name: "name", asc: true }]);
    });

    test("same field asc → sorts descending", async () => {
        const list = makeList({
            orderBy: [{ name: "name", asc: true }],
            _needsReordering: false,
            fields: { name: { name: "name", type: "char" } },
            _cache: makeCache([[1, { resId: 1, data: { name: "A" } }]]),
        });

        await sortBy(list, "name");

        expect(list._loadCalls[0].orderBy).toEqual([{ name: "name", asc: false }]);
    });

    test("same field desc → resets to id asc", async () => {
        const list = makeList({
            orderBy: [{ name: "name", asc: false }],
            _needsReordering: false,
            fields: { id: { name: "id", type: "integer" } },
            _cache: makeCache([[1, { resId: 1, data: {} }]]),
        });

        await sortBy(list, "name");

        expect(list._loadCalls.length).toBe(1);
        expect(list._loadCalls[0].orderBy).toEqual([{ name: "id", asc: true }]);
    });
});

test("paginated selection sorting orders loaded and fetched unset values consistently", async () => {
    const rows = [
        { id: 1, state: "b" },
        { id: 2, state: false },
        { id: 3, state: "a" },
    ];
    const requested = [];
    const model = await makeTestRelationalModel({
        loadRecords: async ({ resIds }) => {
            requested.push([...resIds]);
            return resIds.map((id) => rows.find((row) => row.id === id));
        },
    });
    const list = new StaticList(
        model,
        {
            ...model.config,
            isRoot: false,
            offset: 0,
            limit: 1,
            resIds: [1, 2, 3],
            fields: {
                state: {
                    name: "state",
                    type: "selection",
                    selection: [
                        ["a", "A"],
                        ["b", "B"],
                    ],
                },
            },
            activeFields: { state: makeActiveField() },
        },
        rows.slice(0, 1),
        {
            parent: {
                evalContext: {},
                evalContextWithVirtualIds: {},
                _isEvalContextReady: true,
            },
            onUpdate: async () => {},
        },
    );
    await list.sortBy("state");
    makeLogger("web.model.audit").logic("paginated selection order", {
        ids: list.currentIds,
        requested,
    });
    expect(requested[0]).toEqual([2, 3]);
    expect(list.currentIds).toEqual([2, 3, 1]);
    expect(list.records.map((row) => row.data.state)).toEqual([false]);
    await list.sortBy("state");
    expect(list.currentIds).toEqual([1, 3, 2]);
    expect(list.records.map((row) => row.data.state)).toEqual(["b"]);
});
