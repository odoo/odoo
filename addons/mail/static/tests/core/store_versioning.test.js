import { fields, makeStore, Record, Store } from "@mail/model/export";
import { defineMailModels, start as start2 } from "@mail/../tests/mail_test_helpers";

import { afterEach, beforeEach, expect, test } from "@odoo/hoot";

import { registry } from "@web/core/registry";
import { mockService } from "@web/../tests/web_test_helpers";

function xipToBitmap(xmin, xmax, xip) {
    const bitCount = Number(xmax - xmin);
    if (bitCount <= 0) {
        return "";
    }
    const byteCount = Math.ceil(bitCount / 8);
    const bytes = new Uint8Array(byteCount);
    for (const txid of xip) {
        if (txid >= xmin && txid < xmax) {
            const offset = Number(txid - xmin);
            const byteIndex = Math.floor(offset / 8);
            const bitIndex = offset % 8;
            bytes[byteIndex] |= 1 << bitIndex;
        }
    }
    return btoa(String.fromCharCode(...bytes));
}

const localRegistry = registry.category("discuss.model.test");

defineMailModels();
beforeEach(() => {
    Record.register(localRegistry);
    Store.register(localRegistry);
    mockService("store", (env) => makeStore(env, { localRegistry }));
});
afterEach(() => {
    for (const [modelName] of localRegistry.getEntries()) {
        localRegistry.remove(modelName);
    }
});

async function start() {
    const env = await start2();
    return env.services.store;
}

const SINGLE_FIELD_CASES = [
    {
        name: "keep incoming read if it comes from a newer read snapshot",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v1" },
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v1" },
            },
            {
                values: { name: "v3" },
                meta: { snapshot: { xmin: 40, xmax: 40, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v3" },
                description: "V3 read's snapshot is newer.",
            },
            {
                values: { name: "v2" },
                meta: { snapshot: { xmin: 30, xmax: 30, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v3" },
                description: "V2 read's snapshot is older.",
            },
            {
                values: { name: "v4" },
                meta: {
                    snapshot: {
                        xmin: 65,
                        xmax: 68,
                        xip_bitmap: xipToBitmap(65, 68, [65, 66]),
                        current_xact_id: null,
                    },
                },
                expected: { name: "v4" },
                description: "V4 read's snapshot is newer.",
            },
            {
                values: { name: "v5" },
                meta: {
                    snapshot: {
                        xmin: 65,
                        xmax: 68,
                        xip_bitmap: xipToBitmap(65, 68, [65]),
                        current_xact_id: null,
                    },
                },
                expected: { name: "v5" },
                description:
                    "Same (xmin, xmax) as V4 but one transaction has committed after V4 read but before V5 read.",
            },
        ],
    },
    {
        name: "keep incoming write if the current read version couldn't see the write transaction",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v3" },
                meta: {
                    snapshot: {
                        xmin: 30,
                        xmax: 40,
                        xip_bitmap: xipToBitmap(30, 40, [30, 35]),
                        current_xact_id: null,
                    },
                },
                expected: { name: "v3" },
            },
            {
                values: { name: "v2" },
                meta: {
                    snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: 20 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v3" },
                description: "Write committed before the V3 read.",
            },
            {
                values: { name: "v4" },
                meta: {
                    snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: 35 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v4" },
                description: "Write started before the V3 read but was committed after (xip).",
            },
            {
                values: { name: "v5" },
                meta: { snapshot: { xmin: 40, xmax: 40, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v5" },
                description: "Read after the V4 write committed.",
            },
            {
                values: { name: "v6" },
                meta: {
                    snapshot: { xmin: 50, xmax: 50, xip_bitmap: "", current_xact_id: 50 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v6" },
                description: "Write committed after the V5 read.",
            },
            {
                values: { name: "v7" },
                meta: { snapshot: { xmin: 60, xmax: 60, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v7" },
                description: "Read after the V6 write committed.",
            },
            {
                values: { name: "v8" },
                meta: {
                    snapshot: { xmin: 60, xmax: 60, xip_bitmap: "", current_xact_id: 60 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v8" },
                description: "Write committed at xmax boundary: out of V7 read range.",
            },
        ],
    },
    {
        name: "keep incoming write if the current write version is newer",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v1" },
                meta: {
                    snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: 10 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v1" },
            },
            {
                values: { name: "v3" },
                meta: {
                    snapshot: { xmin: 30, xmax: 30, xip_bitmap: "", current_xact_id: 30 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v3" },
                description: "Write committed after the V1 read.",
            },
            {
                values: { name: "v2" },
                meta: {
                    snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: 20 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v3" },
                description: "Write was committed before the V3 write.",
            },
        ],
    },
    {
        name: "partial update: newer and older reads in the same payload",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v1", description: "desc1" },
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v1", description: "desc1" },
            },
            {
                values: { name: "v3" },
                meta: { snapshot: { xmin: 30, xmax: 30, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v3", description: "desc1" },
            },
            {
                values: { name: "v2", description: "desc2" },
                meta: { snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v3", description: "desc2" },
                description: "Current version has newer name, but not description.",
            },
        ],
    },
    {
        name: "partial update: newer and older writes in the same payload",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v1", description: "desc1" },
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "v1", description: "desc1" },
            },
            {
                values: { name: "v3" },
                meta: {
                    snapshot: { xmin: 30, xmax: 30, xip_bitmap: "", current_xact_id: 30 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "v3", description: "desc1" },
            },
            {
                values: { name: "v2", description: "desc2" },
                meta: {
                    snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: 20 },
                    written_fields_by_record: { Thread: { 1: ["name", "description"] } },
                },
                expected: { name: "v3", description: "desc2" },
                description: "Current version has newer name, but not description.",
            },
        ],
    },
    {
        name: "read cannot override a newer write",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "WRITE" },
                meta: {
                    snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: 10 },
                    written_fields_by_record: { Thread: { 1: ["name"] } },
                },
                expected: { name: "WRITE" },
            },
            {
                values: { name: "READ" },
                meta: { snapshot: { xmin: 5, xmax: 5, xip_bitmap: "", current_xact_id: null } },
                expected: { name: "WRITE" },
                description: "Read from an older snapshot: do not override the write.",
            },
        ],
    },
];

for (const testCase of SINGLE_FIELD_CASES) {
    const testFn = testCase.only ? test.only : test;
    testFn(`single store versionning - ${testCase.name}`, async () => {
        (class Thread extends Record {
            static id = "id";
            id;
            name;
            description;
        }).register(localRegistry);
        const store = await start();
        const thread = store.Thread.insert(testCase.initial);
        for (const step of testCase.steps) {
            store.insert({
                Thread: { id: thread.id, ...step.values },
                __store_version__: step.meta,
            });
            expect(
                Object.fromEntries(
                    Object.keys(step.expected).map((fname) => [fname, thread[fname]])
                )
            ).toEqual(step.expected, { message: step.description });
        }
    });
}

const MANY_FIELD_CASES = [
    {
        name: "keep incoming replace if it comes from a newer replace",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: [["REPLACE", [1, 2, 3]]],
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3],
            },
            {
                values: [["REPLACE", [7, 8, 9]]],
                meta: { snapshot: { xmin: 30, xmax: 30, xip_bitmap: "", current_xact_id: null } },
                expected: [7, 8, 9],
            },
            {
                values: [["REPLACE", [4, 5, 6]]],
                meta: { snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: null } },
                expected: [7, 8, 9],
                description: "Replace is outdated thus ignored.",
            },
        ],
    },
    {
        name: "keep incoming commands if it comes after the base replace",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: [["REPLACE", [1, 2, 3]]],
                meta: { snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3],
            },
            {
                values: [["ADD", [7, 8]]],
                meta: { snapshot: { xmin: 30, xmax: 30, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3, 7, 8],
            },
            {
                values: [["DELETE", [7, 8]]],
                meta: { snapshot: { xmin: 40, xmax: 40, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3],
            },
            {
                values: [["DELETE", [1, 2, 3]]],
                meta: { snapshot: { xmin: 15, xmax: 15, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3],
                description:
                    "Delete command comes from an older snapshot than the base replace: ignored.",
            },
        ],
    },
    {
        name: "commands arriving out of order are properly handled",
        initial: { id: 1, messages: [1, 2, 3] },
        steps: [
            {
                values: [["ADD", [4, 5, 6]]],
                meta: { snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3, 4, 5, 6],
            },
            {
                values: [["DELETE", [1, 4]]],
                meta: { snapshot: { xmin: 15, xmax: 15, xip_bitmap: "", current_xact_id: null } },
                expected: [2, 3, 4, 5, 6],
                description: "4 was added after the delete command, but 1 wasn't.",
            },
        ],
    },
    {
        name: "newer commands arriving before replace are kept",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: [["REPLACE", []]],
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: [],
            },
            {
                values: [["ADD", [4, 5, 6]]],
                meta: { snapshot: { xmin: 20, xmax: 20, xip_bitmap: "", current_xact_id: null } },
                expected: [4, 5, 6],
            },
            {
                values: [["REPLACE", [1]]],
                meta: { snapshot: { xmin: 15, xmax: 15, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 4, 5, 6],
                description:
                    "Replace came before the ADD, even if it was received after: add is kept.",
            },
        ],
    },
    {
        name: "keep command with equivalent snapshot as the last replace when they come after it",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: [["REPLACE", [1, 2, 3]]],
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3],
            },
            {
                values: [["ADD", [4, 5, 6]]],
                meta: { snapshot: { xmin: 10, xmax: 10, xip_bitmap: "", current_xact_id: null } },
                expected: [1, 2, 3, 4, 5, 6],
            },
        ],
    },
];

for (const testCase of MANY_FIELD_CASES) {
    const testFn = testCase.only ? test.only : test;
    testFn(`many store versionning - ${testCase.name}`, async () => {
        (class Message extends Record {
            static id = "id";
            id;
        }).register(localRegistry);
        (class Thread extends Record {
            static id = "id";
            id;
            messages = fields.Many("Message");
        }).register(localRegistry);
        const store = await start();
        const thread = store.Thread.insert(testCase.initial);
        for (const step of testCase.steps) {
            store.insert({
                Thread: { id: thread.id, messages: step.values },
                __store_version__: step.meta,
            });
            expect(thread.messages.map(({ id }) => id).sort()).toEqual(step.expected, {
                message: step.description,
            });
        }
    });
}

test("Inverse of relations are properly versioned", async () => {
    (class Message extends Record {
        static id = "id";
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);

    (class Thread extends Record {
        static id = "id";
        messages = fields.Many("Message", { inverse: "thread" });
    }).register(localRegistry);

    const store = await start();
    store.Thread.insert([1, 2, 3]);
    store.insert({
        Thread: { id: 1, messages: [["REPLACE", [1, 2]]] },
        __store_version__: { snapshot: { xmin: 1, xmax: 1, xip_bitmap: "" } },
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([1, 2]);
    expect(store.Message.get(1).thread.id).toBe(1);
    store.insert({
        Thread: { id: 1, messages: [["DELETE", [1]]] },
        __store_version__: { snapshot: { xmin: 3, xmax: 3, xip_bitmap: "" } },
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2]);
    expect(store.Message.get(1).thread).toBe(undefined);
    // Outdated update on the one side, shouldn't update the relation.
    store.insert({
        Message: { id: 1, thread: 1 },
        __store_version__: { snapshot: { xmin: 2, xmax: 2, xip_bitmap: "" } },
    });
    expect(store.Message.get(1).thread).toBe(undefined);
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2]);
    store.insert({
        Message: { id: 1, thread: 1 },
        __store_version__: { snapshot: { xmin: 4, xmax: 4, xip_bitmap: "" } },
    });
    expect(store.Message.get(1).thread.id).toBe(1);
    expect(
        store.Thread.get(1)
            .messages.map((m) => m.id)
            .sort()
    ).toEqual([1, 2]);
    // Outdated delete on the many side, shouldn't impact the relation.
    store.insert({
        Thread: { id: 1, messages: [["DELETE", [1]]] },
        __store_version__: { snapshot: { xmin: 3, xmax: 3, xip_bitmap: "" } },
    });
    expect(
        store.Thread.get(1)
            .messages.map((m) => m.id)
            .sort()
    ).toEqual([1, 2]);
    expect(store.Message.get(1).thread.id).toBe(1);
});
