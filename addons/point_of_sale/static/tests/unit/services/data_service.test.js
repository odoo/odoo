import { test, expect, describe, beforeEach } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { freezeDate, getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("data_service", () => {
    test("localDeleteCascade", async () => {
        const store = await setupPosEnv();
        const data = store.data;
        const order = await getFilledOrder(store);

        expect(store.models["pos.order"].length).toBe(1);
        expect(store.models["pos.order.line"].length).toBe(2);
        data.localDeleteCascade(order);
        expect(store.models["pos.order"].length).toBe(0);
        expect(store.models["pos.order.line"].length).toBe(0);
    });
});

describe("initListeners", () => {
    beforeEach(() => {
        odoo.screen_type = "terminal";
    });

    test("initialises state and registers all webrtc handlers", async () => {
        const store = await setupPosEnv();
        expect(store.data.ignoredSyncs).toBeInstanceOf(Set);
        expect(store.data.ignoredSyncs.size).toBe(0);
        expect(store.data._deletedKeys).toEqual({});
        let resolved = false;
        store.data._syncQueue.then(() => {
            resolved = true;
        });
        await store.data._syncQueue;
        expect(resolved).toBe(true);
        expect(store.data.webrtc._registry.get("sync")).toBeInstanceOf(Function);
        expect(store.data.webrtc._snapshotRegistry.get("sync")?.build).toBeInstanceOf(Function);
        expect(store.data.webrtc._snapshotRegistry.get("sync")?.apply).toBeInstanceOf(Function);
    });

    test("calls broadcaster and routes each model to dynamic or static listener", async () => {
        const store = await setupPosEnv();
        const broadcastedCalls = [];
        const staticCalls = [];
        const dynamicCalls = [];
        let calledConnectWebSocket = false;
        patchWithCleanup(store.data, {
            connectWebSocket(channel, method) {
                calledConnectWebSocket =
                    channel === "SERVER_SYNCHRONISATION" &&
                    method.name === "bound _handleServerSync";
            },
            relations: { "pos.order": {}, "product.template": {} },
            _registerModelBroadcaster(model) {
                broadcastedCalls.push(model);
            },
            dynamicModelListener(model) {
                dynamicCalls.push(model);
            },
            staticModelListener(model) {
                staticCalls.push(model);
            },
        });
        patchWithCleanup(store.data.opts, { dynamicModels: ["pos.order"] });
        store.data.initListeners();
        expect(calledConnectWebSocket).toBe(true);
        expect(broadcastedCalls).toEqual(["pos.order", "product.template"]);
        expect(dynamicCalls).toEqual(["pos.order"]);
        expect(staticCalls).toEqual(["product.template"]);
    });

    describe("this.webrtc.register('sync')", () => {
        test("sync handler calls _handlePeerSync with from and payload", async () => {
            const store = await setupPosEnv();
            let called = null;
            patchWithCleanup(store.data, {
                _handlePeerSync(from, payload) {
                    called = { from, payload };
                },
            });
            store.data.webrtc._registry.get("sync")(
                { id: "peer-1", group: "terminal", deviceUuid: null },
                { data: "x" }
            );
            await store.data._syncQueue;
            expect(called).toEqual({ from: "peer-1", payload: { data: "x" } });
        });

        test("sync handler queues successive calls so each waits for the previous", async () => {
            const store = await setupPosEnv();
            const order = [];
            const { promise: blocker, resolve: unblock } = Promise.withResolvers();
            patchWithCleanup(store.data, {
                async _handlePeerSync(from) {
                    if (from === "peer-1") {
                        await blocker;
                    }
                    order.push(from);
                },
            });
            const handler = store.data.webrtc._registry.get("sync");
            handler({ id: "peer-1", group: "terminal", deviceUuid: null }, {});
            handler({ id: "peer-2", group: "terminal", deviceUuid: null }, {});
            unblock();
            await store.data._syncQueue;
            expect(order).toEqual(["peer-1", "peer-2"]);
        });

        test("sync queue continues after a handler error", async () => {
            const store = await setupPosEnv();
            const order = [];
            patchWithCleanup(store.data, {
                async _handlePeerSync(from) {
                    if (from === "peer-1") {
                        throw new Error("boom");
                    }
                    order.push(from);
                },
            });
            const handler = store.data.webrtc._registry.get("sync");
            handler({ id: "peer-1", group: "terminal", deviceUuid: null }, {});
            handler({ id: "peer-2", group: "terminal", deviceUuid: null }, {});
            await expect(store.data._syncQueue).resolves.toBe(undefined);
            expect(order).toEqual(["peer-2"]);
        });
    });

    describe("webrtc.registerSnapshot('sync').apply", () => {
        test("calls _handleSnapshot with from, group and payload", async () => {
            const store = await setupPosEnv();
            let called = null;
            patchWithCleanup(store.data, {
                _handleSnapshot(from, group, payload) {
                    called = { from, group, payload };
                },
            });
            store.data.webrtc._snapshotRegistry
                .get("sync")
                .apply({ id: "peer-1", group: "terminal", deviceUuid: null }, { data: "x" });
            await store.data._syncQueue;
            expect(called).toEqual({ from: "peer-1", group: "terminal", payload: { data: "x" } });
        });

        test("queues successive calls so each waits for the previous", async () => {
            const store = await setupPosEnv();
            const order = [];
            const { promise: blocker, resolve: unblock } = Promise.withResolvers();
            patchWithCleanup(store.data, {
                async _handleSnapshot(from) {
                    if (from === "peer-1") {
                        await blocker;
                    }
                    order.push(from);
                },
            });
            const apply = store.data.webrtc._snapshotRegistry.get("sync").apply;
            apply({ id: "peer-1", group: "terminal", deviceUuid: null }, {});
            apply({ id: "peer-2", group: "terminal", deviceUuid: null }, {});
            unblock();
            await store.data._syncQueue;
            expect(order).toEqual(["peer-1", "peer-2"]);
        });

        test("queue continues after a handler error", async () => {
            const store = await setupPosEnv();
            const order = [];
            patchWithCleanup(store.data, {
                async _handleSnapshot(from) {
                    if (from === "peer-1") {
                        throw new Error("boom");
                    }
                    order.push(from);
                },
            });
            const apply = store.data.webrtc._snapshotRegistry.get("sync").apply;
            apply({ id: "peer-1", group: "terminal", deviceUuid: null }, {});
            apply({ id: "peer-2", group: "terminal", deviceUuid: null }, {});
            await store.data._syncQueue;
            expect(order).toEqual(["peer-2"]);
        });
    });

    describe("webrtc.registerSnapshot('sync').build", () => {
        test("returns full sync payload for terminal peers", async () => {
            const store = await setupPosEnv();
            const fakePayload = { records: { "pos.order": { "uuid-x": {} } }, deleted: {} };
            patchWithCleanup(store.data, {
                _buildFullSyncPayload() {
                    return fakePayload;
                },
            });
            const result = store.data.webrtc._snapshotRegistry
                .get("sync")
                .build({ id: "peer-1", group: "terminal", deviceUuid: null });
            expect(result).toEqual(fakePayload);
        });

        test("returns null when payload is empty", async () => {
            const store = await setupPosEnv();
            patchWithCleanup(store.data, {
                _buildFullSyncPayload() {
                    return { records: {}, deleted: {} };
                },
            });
            const result = store.data.webrtc._snapshotRegistry
                .get("sync")
                .build({ id: "peer-1", group: "terminal", deviceUuid: null });
            expect(result).toBe(null);
        });

        test("returns null for non-terminal peers", async () => {
            const store = await setupPosEnv();
            const result = store.data.webrtc._snapshotRegistry
                .get("sync")
                .build({ id: "peer-1", group: "cashier", deviceUuid: null });
            expect(result).toBe(null);
        });
    });
});

describe("_trackMutation", () => {
    test("update stamps each listed field with the same timestamp", async () => {
        const ts = freezeDate("2020-01-01");
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.data._trackMutation("pos.order", "update", {
            id: order.id,
            fields: ["_note", "_ref"],
        });
        expect(order._mutations._note).toBe(ts);
        expect(order._mutations._ref).toBe(ts);
    });

    test("update overwrites an earlier mutation timestamp", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const first = freezeDate("2020-01-01");
        store.data._trackMutation("pos.order", "update", { id: order.id, fields: ["_note"] });
        expect(order._mutations._note).toBe(first);

        const second = freezeDate("2020-01-02");
        store.data._trackMutation("pos.order", "update", { id: order.id, fields: ["_note"] });
        expect(order._mutations._note).toBe(second);
    });

    test("update is a no-op when record does not exist", async () => {
        const store = await setupPosEnv();
        expect(() =>
            store.data._trackMutation("pos.order", "update", { id: -1, fields: ["_note"] })
        ).not.toThrow();
    });

    test("delete adds the record uuid to _deletedKeys", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.data._trackMutation("pos.order", "delete", { key: order.uuid });
        expect(store.data._deletedKeys["pos.order"]?.has(order.uuid)).toBe(true);
    });
});

describe("_buildFullSyncPayload", () => {
    test("includes orders keyed by uuid with serialized data", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order.serializeForIndexedDB = () => ({ uuid: order.uuid });
        order._mutations = {};

        const { records, deleted } = store.data._buildFullSyncPayload();
        expect(records["pos.order"][order.uuid]).toEqual({
            data: { uuid: order.uuid },
            meta: { mutations: {} },
        });
        expect(deleted).toEqual({});
    });

    test("includes mutations in the payload", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order.serializeForIndexedDB = () => ({ uuid: order.uuid });
        order._mutations = { _note: 1000 };

        const { records } = store.data._buildFullSyncPayload();
        expect(records["pos.order"][order.uuid]).toEqual({
            data: { uuid: order.uuid },
            meta: { mutations: { _note: 1000 } },
        });
    });

    test("serializes _deletedKeys as an array in deleted", async () => {
        const store = await setupPosEnv();
        store.data._deletedKeys["pos.order"] = new Set(["uuid-a", "uuid-b"]);
        const { deleted } = store.data._buildFullSyncPayload();
        expect(deleted["pos.order"]).toEqual(["uuid-a", "uuid-b"]);
    });
});

describe("_registerModelBroadcaster", () => {
    const spyWebrtc = (store) => {
        const calls = [];
        patchWithCleanup(store.data.webrtc, {
            pushMessage(action, payload, options) {
                calls.push(["pushMessage", { action, payload, options }]);
            },
            debounceSendMessages() {
                calls.push("debounceSendMessages");
            },
        });
        return calls;
    };

    test("broadcasts create event with serialized record and calls _trackMutation", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order.serializeForIndexedDB = () => ({ uuid: order.uuid });
        order._mutations = {};
        const webrtcCalls = spyWebrtc(store);
        store.models["pos.order"].triggerEvents("create", { ids: [order.id] });
        expect(webrtcCalls).toEqual([
            [
                "pushMessage",
                {
                    action: "sync",
                    payload: [
                        {
                            event: "create",
                            model: "pos.order",
                            key: "uuid",
                            records: [{ data: { uuid: order.uuid }, meta: { mutations: {} } }],
                        },
                    ],
                    options: { group: "terminal" },
                },
            ],
            "debounceSendMessages",
        ]);
    });

    test("broadcasts update event with mutated field timestamp", async () => {
        const ts = freezeDate("2020-01-01");
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order.serializeForIndexedDB = () => ({ uuid: order.uuid });
        order._mutations = {};
        const calls = spyWebrtc(store);
        store.models["pos.order"].triggerEvents("update", { id: order.id, fields: ["_note"] });
        expect(calls).toEqual([
            [
                "pushMessage",
                {
                    action: "sync",
                    payload: [
                        {
                            event: "update",
                            model: "pos.order",
                            key: "uuid",
                            records: [
                                { data: { uuid: order.uuid }, meta: { mutations: { _note: ts } } },
                            ],
                        },
                    ],
                    options: { group: "terminal" },
                },
            ],
            "debounceSendMessages",
        ]);
    });

    test("broadcasts delete event with id fallback when record is gone", async () => {
        const store = await setupPosEnv();
        const calls = spyWebrtc(store);
        store.models["pos.order"].triggerEvents("delete", { ids: [-1], key: "fake-uuid" });
        expect(calls).toEqual([
            [
                "pushMessage",
                {
                    action: "sync",
                    payload: [
                        {
                            event: "delete",
                            model: "pos.order",
                            key: "uuid",
                            records: [
                                { data: { id: -1, uuid: "fake-uuid" }, meta: { mutations: {} } },
                            ],
                        },
                    ],
                    options: { group: "terminal" },
                },
            ],
            "debounceSendMessages",
        ]);
    });

    test("skips pushMessage and debounceSendMessages when syncId is in ignoredSyncs", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.data.ignoredSyncs.add("sync-abc");
        const calls = spyWebrtc(store);
        store.models["pos.order"].triggerEvents("create", { ids: [order.id], syncId: "sync-abc" });
        expect(calls).toEqual([]);
    });
});

describe("_handleServerSync", () => {
    test("passes records and empty deletionsByModel to _applyParsedSync", async () => {
        const store = await setupPosEnv();
        let applyArgs = null;
        patchWithCleanup(store.data, {
            async _applyParsedSync(resolved, deletionsByModel) {
                applyArgs = { resolved, deletionsByModel };
            },
        });
        const records = { "pos.order": [{ uuid: "test-uuid" }] };
        await store.data._handleServerSync({ records });
        expect(applyArgs.resolved).toEqual(records);
        expect(applyArgs.deletionsByModel).toEqual({});
    });

    test("converts deleted_record_ids arrays to Sets before delegating", async () => {
        const store = await setupPosEnv();
        let applyArgs = null;
        patchWithCleanup(store.data, {
            async _applyParsedSync(resolved, deletionsByModel) {
                applyArgs = { resolved, deletionsByModel };
            },
        });
        await store.data._handleServerSync({
            records: {},
            deleted_record_ids: { "pos.order": [1, 2] },
        });
        expect(applyArgs.deletionsByModel).toEqual({ "pos.order": new Set([1, 2]) });
    });
});

describe("_handlePeerSync", () => {
    test("merges and resolves the payload then delegates to _applyParsedSync", async () => {
        const store = await setupPosEnv();
        let applyArgs = null;
        patchWithCleanup(store.data, {
            async _applyParsedSync(resolved, deletionsByModel) {
                applyArgs = { resolved, deletionsByModel };
            },
        });
        const payload = [
            {
                event: "create",
                model: "pos.order",
                key: "uuid",
                records: [{ data: { id: 99, uuid: "test-uuid" }, meta: { mutations: {} } }],
            },
        ];
        await store.data._handlePeerSync("peer-1", payload);
        expect(applyArgs.resolved["pos.order"]).toEqual([{ id: 99, uuid: "test-uuid" }]);
        expect(applyArgs.deletionsByModel).toEqual({ "pos.order": new Set() });
    });
});

describe("_handleSnapshot", () => {
    test("does nothing when group is not terminal", async () => {
        const store = await setupPosEnv();
        let called = false;
        patchWithCleanup(store.data, {
            async _applyParsedSync() {
                called = true;
            },
        });
        await store.data._handleSnapshot("peer-1", "cashier", { records: {}, deleted: {} });
        expect(called).toBe(false);
    });

    test("resolves conflicts and delegates to _applyParsedSync for terminal group", async () => {
        const store = await setupPosEnv();
        let applyArgs = null;
        patchWithCleanup(store.data, {
            async _applyParsedSync(resolved, deletionsByModel) {
                applyArgs = { resolved, deletionsByModel };
            },
        });
        const records = {
            "pos.order": {
                "uuid-x": { data: { id: 1, uuid: "uuid-x" }, meta: { mutations: {} } },
            },
        };
        await store.data._handleSnapshot("peer-1", "terminal", {
            records,
            deleted: { "pos.order": ["uuid-del"] },
        });
        expect(applyArgs.resolved["pos.order"]).toEqual([{ id: 1, uuid: "uuid-x" }]);
        expect(applyArgs.deletionsByModel).toEqual({ "pos.order": new Set(["uuid-del"]) });
    });
});

describe("_applyParsedSync", () => {
    test("connects resolved records to the store", async () => {
        const store = await setupPosEnv();
        let connected = null;
        patchWithCleanup(store.data, {
            async missingRecursive(data) {
                return data;
            },
        });
        patchWithCleanup(store.models, {
            connectNewData(data) {
                connected = data;
                return [];
            },
        });
        const resolved = { "pos.order": [{ id: 99, uuid: "test-uuid" }] };
        await store.data._applyParsedSync(resolved, {});
        expect(connected["pos.order"]).toEqual([{ id: 99, uuid: "test-uuid" }]);
    });

    test("applies deletions", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        patchWithCleanup(store.data, {
            async missingRecursive(data) {
                return data;
            },
        });
        await store.data._applyParsedSync({}, { "pos.order": new Set([order.uuid]) });
        expect(store.models["pos.order"].get(order.id)).toBe(undefined);
    });

    test("adds syncId to ignoredSyncs while processing and removes it after", async () => {
        const store = await setupPosEnv();
        let sizeWhileProcessing = null;
        patchWithCleanup(store.data, {
            async missingRecursive(data) {
                sizeWhileProcessing = store.data.ignoredSyncs.size;
                return data;
            },
        });
        patchWithCleanup(store.models, {
            connectNewData() {
                return [];
            },
        });
        expect(store.data.ignoredSyncs.size).toBe(0);
        await store.data._applyParsedSync({}, {});
        expect(sizeWhileProcessing).toBe(1);
        await Promise.resolve(); // flush queueMicrotask that removes the syncId
        expect(store.data.ignoredSyncs.size).toBe(0);
    });
});

describe("_applyDeletions", () => {
    test("removes records matching the uuid set", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.data._applyDeletions({ "pos.order": new Set([order.uuid]) });
        expect(store.models["pos.order"].get(order.id)).toBe(undefined);
    });

    test("leaves records not in the set untouched", async () => {
        const store = await setupPosEnv();
        const order1 = store.addNewOrder();
        const order2 = store.addNewOrder();
        store.data._applyDeletions({ "pos.order": new Set([order1.uuid]) });
        expect(store.models["pos.order"].get(order1.id)).toBe(undefined);
        expect(store.models["pos.order"].get(order2.id)).not.toBe(undefined);
    });

    test("is a no-op for an empty set", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.data._applyDeletions({ "pos.order": new Set() });
        expect(store.models["pos.order"].get(order.id)).not.toBe(undefined);
    });

    test("deletes by id when model has no databaseTable key", async () => {
        const store = await setupPosEnv();
        const product = store.models["product.template"].get(5);
        store.data._applyDeletions({ "product.template": new Set([product.id]) });
        expect(store.models["product.template"].get(product.id)).toBe(undefined);
    });
});

describe("_isDeletedOrder", () => {
    test("returns true for pos.order with empty lines", async () => {
        const store = await setupPosEnv();
        expect(store.data._isDeletedOrder("pos.order", { lines: [] })).toBe(true);
    });

    test("returns false for pos.order with at least one line", async () => {
        const store = await setupPosEnv();
        expect(store.data._isDeletedOrder("pos.order", { lines: [1] })).toBe(false);
    });

    test("returns false for other models even with empty lines", async () => {
        const store = await setupPosEnv();
        expect(store.data._isDeletedOrder("pos.order.line", { lines: [] })).toBe(false);
    });

    test("returns false when lines is absent", async () => {
        const store = await setupPosEnv();
        expect(store.data._isDeletedOrder("pos.order", {})).toBe(false);
    });
});

describe("_mergePeerSyncs", () => {
    const makeSync = (event, data, mutations = {}) => ({
        event,
        model: "pos.order",
        key: "uuid",
        records: [{ data, meta: { mutations } }],
    });

    test("create populates recordsByModel", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("create", { id: 1, uuid: "abc" }),
        ]);
        expect(recordsByModel).toEqual({
            "pos.order": { abc: { data: { id: 1, uuid: "abc" }, meta: { mutations: {} } } },
        });
        expect(deletionsByModel).toEqual({ "pos.order": new Set() });
    });

    test("update without prior create still populates recordsByModel", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("update", { id: 1, uuid: "abc", _state: "b" }, { _state: 1000 }),
        ]);
        expect(recordsByModel).toEqual({
            "pos.order": {
                abc: {
                    data: { id: 1, uuid: "abc", _state: "b" },
                    meta: { mutations: { _state: 1000 } },
                },
            },
        });
        expect(deletionsByModel).toEqual({ "pos.order": new Set() });
    });

    test("create then update: update data and mutations win", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("create", { id: 1, uuid: "abc", _state: "a" }),
            makeSync("update", { id: 1, uuid: "abc", _state: "b" }, { _state: 1000 }),
        ]);
        expect(recordsByModel).toEqual({
            "pos.order": {
                abc: {
                    data: { id: 1, uuid: "abc", _state: "b" },
                    meta: { mutations: { _state: 1000 } },
                },
            },
        });
        expect(deletionsByModel).toEqual({ "pos.order": new Set() });
    });

    test("update then create: create is ignored, update data is kept", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("update", { id: 1, uuid: "abc", _state: "a" }, { _state: 500 }),
            makeSync("create", { id: 1, uuid: "abc", _state: "b" }),
        ]);
        expect(recordsByModel).toEqual({
            "pos.order": {
                abc: {
                    data: { id: 1, uuid: "abc", _state: "a" },
                    meta: { mutations: { _state: 500 } },
                },
            },
        });
        expect(deletionsByModel).toEqual({ "pos.order": new Set() });
    });

    test("last update wins", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("update", { id: 1, uuid: "abc", _state: "a" }, { _state: 500 }),
            makeSync("update", { id: 1, uuid: "abc", _state: "b" }, { _state: 550 }),
        ]);
        expect(recordsByModel).toEqual({
            "pos.order": {
                abc: {
                    data: { id: 1, uuid: "abc", _state: "b" },
                    meta: { mutations: { _state: 550 } },
                },
            },
        });
        expect(deletionsByModel).toEqual({ "pos.order": new Set() });
    });

    test("delete removes record and adds key to deletionsByModel", async () => {
        const store = await setupPosEnv();
        // delete payload includes uuid via [modelKey]: params.key (fixed in _registerModelBroadcaster)
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("create", { id: 1, uuid: "abc" }),
            makeSync("delete", { id: 1, uuid: "abc" }),
        ]);
        expect(recordsByModel).toEqual({ "pos.order": {} });
        expect(deletionsByModel).toEqual({ "pos.order": new Set(["abc"]) });
    });

    test("create after delete is skipped", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("delete", { id: 1, uuid: "abc" }),
            makeSync("create", { id: 1, uuid: "abc" }),
        ]);
        expect(recordsByModel).toEqual({ "pos.order": {} });
        expect(deletionsByModel).toEqual({ "pos.order": new Set(["abc"]) });
    });

    test("pos.order with empty lines is treated as deleted", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("create", { id: 1, uuid: "abc", lines: [] }),
        ]);
        expect(recordsByModel).toEqual({ "pos.order": {} });
        expect(deletionsByModel).toEqual({ "pos.order": new Set(["abc"]) });
    });

    test("falls back to data.id as key when data[key] is undefined", async () => {
        const store = await setupPosEnv();
        const { recordsByModel, deletionsByModel } = store.data._mergePeerSyncs([
            makeSync("create", { id: 42 }),
        ]);
        expect(recordsByModel).toEqual({
            "pos.order": { 42: { data: { id: 42 }, meta: { mutations: {} } } },
        });
        expect(deletionsByModel).toEqual({ "pos.order": new Set() });
    });
});

describe("_resolveConflicts", () => {
    const makeInput = (key, data, mutations = {}) => ({
        "pos.order": { [key]: { data, meta: { mutations } } },
    });

    test("returns remote data as-is when no local record exists", async () => {
        const store = await setupPosEnv();
        const result = store.data._resolveConflicts(
            makeInput("non-existent", { id: 1, uuid: "non-existent", _val: "remote" })
        );
        expect(result).toEqual({ "pos.order": [{ id: 1, uuid: "non-existent", _val: "remote" }] });
    });

    test("skips record that was locally deleted", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.data._deletedKeys["pos.order"] = new Set([order.uuid]);

        const result = store.data._resolveConflicts(
            makeInput(order.uuid, { id: order.id, uuid: order.uuid })
        );
        expect(result).toEqual({ "pos.order": [] });
    });

    test("local field wins when local mutation is more recent", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order._note = "local";
        order._mutations._note = 2000;

        const result = store.data._resolveConflicts({
            "pos.order": {
                [order.uuid]: {
                    data: { ...order.serializeForIndexedDB(), _note: "remote" },
                    meta: { mutations: { _note: 1000 } },
                },
            },
        });
        expect(result["pos.order"][0]._note).toBe("local");
    });

    test("remote field wins when remote mutation is more recent", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order._note = "local";
        order._mutations._note = 500;

        const result = store.data._resolveConflicts({
            "pos.order": {
                [order.uuid]: {
                    data: { ...order.serializeForIndexedDB(), _note: "remote" },
                    meta: { mutations: { _note: 1000 } },
                },
            },
        });
        expect(result["pos.order"][0]._note).toBe("remote");
    });

    test("remote wins when timestamps are equal", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order._note = "local";
        order._mutations._note = 1000;

        const result = store.data._resolveConflicts({
            "pos.order": {
                [order.uuid]: {
                    data: { ...order.serializeForIndexedDB(), _note: "remote" },
                    meta: { mutations: { _note: 1000 } },
                },
            },
        });
        expect(result["pos.order"][0]._note).toBe("remote");
    });

    test("remote wins when no local mutation exists for the field", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        // _mutations._note intentionally not set

        const result = store.data._resolveConflicts({
            "pos.order": {
                [order.uuid]: {
                    data: { ...order.serializeForIndexedDB(), _note: "remote" },
                    meta: { mutations: { _note: 1000 } },
                },
            },
        });
        expect(result["pos.order"][0]._note).toBe("remote");
    });

    test("resolution is field-level: local wins on one field, remote wins on another", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order._note = "local";
        order._mutations._note = 2000; // local newer → local wins
        order._mutations._ref = 500; // remote newer → remote wins

        const result = store.data._resolveConflicts({
            "pos.order": {
                [order.uuid]: {
                    data: { ...order.serializeForIndexedDB(), _note: "remote", _ref: "remote-ref" },
                    meta: { mutations: { _note: 1000, _ref: 1000 } },
                },
            },
        });
        expect(result["pos.order"][0]._note).toBe("local");
        expect(result["pos.order"][0]._ref).toBe("remote-ref");
    });
});
