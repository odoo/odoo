import { AND, fields, makeStore, Record, Store } from "@mail/model/export";
import { defineMailModels, start as start2 } from "@mail/../tests/mail_test_helpers";

import { afterEach, beforeEach, expect, test } from "@odoo/hoot";

import { registry } from "@web/core/registry";
import { getService, mockService } from "@web/../tests/web_test_helpers";

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
    await start2();
    return getService("store");
}

const SINGLE_FIELD_CASES = [
    {
        name: "keep incoming record if it comes from a newer version",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v1", __version__: "2026-08-01T00:00:10.000000" },
                expected: { name: "v1" },
            },
            {
                values: { name: "v3", __version__: "2026-08-01T00:00:40.000000" },
                expected: { name: "v3" },
                description: "V3's version is newer.",
            },
            {
                values: { name: "v2", __version__: "2026-08-01T00:00:30.000000" },
                expected: { name: "v3" },
                description: "V2's version is older.",
            },
        ],
    },
    {
        name: "partial update: newer and older versions in the same payload",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: {
                    name: "v1",
                    description: "desc1",
                    __version__: "2026-08-01T00:00:10.000000",
                },
                expected: { name: "v1", description: "desc1" },
            },
            {
                values: { name: "v3", __version__: "2026-08-01T00:00:30.000000" },
                expected: { name: "v3", description: "desc1" },
            },
            {
                values: {
                    name: "v2",
                    description: "desc2",
                    __version__: "2026-08-01T00:00:20.000000",
                },
                expected: { name: "v3", description: "desc2" },
                description: "Current version has newer name, but not description.",
            },
        ],
    },
    {
        name: "older version cannot override a newer version",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v2", __version__: "2026-08-01T00:00:10.000000" },
                expected: { name: "v2" },
            },
            {
                values: { name: "v1", __version__: "2026-08-01T00:00:05.000000" },
                expected: { name: "v2" },
                description: "Older version does not override newer version.",
            },
        ],
    },
    {
        name: "microsecond precision is not lost within the same millisecond",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v2", __version__: "2026-08-01T00:00:10.123999" },
                expected: { name: "v2" },
            },
            {
                values: { name: "v1", __version__: "2026-08-01T00:00:10.123456" },
                expected: { name: "v2" },
                description:
                    "v1 is chronologically older than v2. a millisecond-only comparison would see them as equal.",
            },
        ],
    },
];

for (const testCase of SINGLE_FIELD_CASES) {
    const testFn = testCase.only ? test.only : test;
    testFn(`single store versioning - ${testCase.name}`, async () => {
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
        name: "latest arrived replace wins",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: {
                    messages: [["REPLACE", [1, 2, 3]]],
                    __version__: "2026-08-01T00:00:10.000000",
                },
                expected: [1, 2, 3],
            },
            {
                values: {
                    messages: [["REPLACE", [7, 8, 9]]],
                    __version__: "2026-08-01T00:00:30.000000",
                },
                expected: [7, 8, 9],
            },
        ],
    },
    {
        name: "keep incoming commands coming after the base replace",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: { messages: [["REPLACE", [1, 2, 3]]] },
                expected: [1, 2, 3],
            },
            {
                values: {
                    messages: [
                        [
                            "ADD",
                            [
                                { id: 7, __version__: "2026-08-01T00:00:30.000000" },
                                { id: 8, __version__: "2026-08-01T00:00:30.000000" },
                            ],
                        ],
                    ],
                },
                expected: [1, 2, 3, 7, 8],
            },
            {
                values: {
                    messages: [
                        [
                            "DELETE",
                            [
                                { id: 7, __version__: "2026-08-01T00:00:40.000000" },
                                { id: 8, __version__: "2026-08-01T00:00:40.000000" },
                            ],
                        ],
                    ],
                },
                expected: [1, 2, 3],
            },
        ],
    },
    {
        name: "commands arriving out of order are properly handled",
        initial: { id: 1, messages: [1, 2, 3] },
        steps: [
            {
                values: {
                    messages: [
                        [
                            "ADD",
                            [
                                { id: 4, __version__: "2026-08-01T00:00:10.000000" },
                                { id: 5, __version__: "2026-08-01T00:00:20.000000" },
                                { id: 6, __version__: "2026-08-01T00:00:20.000000" },
                            ],
                        ],
                    ],
                },
                expected: [1, 2, 3, 4, 5, 6],
            },
            {
                values: {
                    messages: [
                        [
                            "DELETE",
                            [
                                { id: 4, __version__: "2026-08-01T00:00:15.000000" },
                                { id: 5, __version__: "2026-08-01T00:00:15.000000" },
                            ],
                        ],
                    ],
                },
                expected: [1, 2, 3, 5, 6],
                description: "4 was added before the delete command, but 5 wasn't.",
            },
        ],
    },
    {
        name: "commands arriving before replace are not kept",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: { messages: [["REPLACE", []]] },
                expected: [],
            },
            {
                values: {
                    messages: [
                        [
                            "ADD",
                            [
                                { id: 4, __version__: "2026-08-01T00:00:20.000000" },
                                { id: 5, __version__: "2026-08-01T00:00:20.000000" },
                                { id: 6, __version__: "2026-08-01T00:00:20.000000" },
                            ],
                        ],
                    ],
                },
                expected: [4, 5, 6],
            },
            {
                values: { messages: [["REPLACE", [1]]] },
                expected: [1],
            },
        ],
    },
    {
        name: "values with equal versions keep their arrival order",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: { messages: [["REPLACE", [1, 2, 3]]] },
                expected: [1, 2, 3],
            },
            {
                values: {
                    messages: [["ADD", [{ id: 4, __version__: "2026-08-01T00:00:10.000000" }]]],
                },
                expected: [1, 2, 3, 4],
            },
            {
                values: {
                    messages: [["DELETE", [{ id: 4, __version__: "2026-08-01T00:00:10.000000" }]]],
                },
                expected: [1, 2, 3],
            },
        ],
    },
];

for (const testCase of MANY_FIELD_CASES) {
    const testFn = testCase.only ? test.only : test;
    testFn(`many store versioning - ${testCase.name}`, async () => {
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
                Thread: { id: thread.id, ...step.values },
            });
            expect(thread.messages.map(({ id }) => id).sort()).toEqual(step.expected, {
                message: step.description,
            });
        }
    });
}

test("out-of-order delete does not pile up inverse echoes", async () => {
    (class Message extends Record {
        static id = "id";
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);

    (class Thread extends Record {
        static id = "id";
        messages = fields.Many("Message", { inverse: "thread" });
    }).register(localRegistry);

    const store = await start();
    store.insert({
        Thread: { id: 1, messages: [["REPLACE", [1, 2, 3, 4, 5]]] },
    });
    store.insert({
        Thread: { id: 1, messages: [["ADD", [6], "2026-08-01T00:00:30.000000"]] },
    });
    store.insert({
        Thread: { id: 1, messages: [["DELETE", [1], "2026-08-01T00:00:20.000000"]] },
    });
    // Echoes are kept in history as they are required to correctly compute an equivalent replace command.
    expect(store.Thread.get(1)._.fieldsVersion.get("messages").history.length).toBe(6);
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2, 3, 4, 5, 6]);
    expect(store.Message.get(1).thread).toBe(undefined);
});

test("inverse echo follows the field it mirrors", async () => {
    (class Message extends Record {
        static id = "id";
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);

    (class Thread extends Record {
        static id = "id";
        messages = fields.Many("Message", { inverse: "thread" });
    }).register(localRegistry);

    const store = await start();
    store.insert({
        Message: { id: 1, thread: 9, __version__: "2026-08-01T00:00:30.000000" },
    });
    store.insert({
        Thread: { id: 1, messages: [["REPLACE", [1]]] },
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([1]);
    expect(store.Message.get(1).thread.id).toBe(1);
});

test("a replace keeps the order it was sent in", async () => {
    // Regression test: values used to be placed in the history by their own version, which
    // reordered them by write date instead of keeping the order the server sent.
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
    const thread = store.Thread.insert({ id: 1, messages: [] });
    store.insert({ Thread: { id: 1, messages: [["REPLACE", [3, 1, 2]]] } });
    expect(thread.messages.map(({ id }) => id)).toEqual([3, 1, 2]);
});

test("values are deduplicated when the owner model has a compound id", async () => {
    // Regression test: with a compound owner id, values of a replayed history used to resolve
    // to different localIds than the ones already in the relation, and get registered twice.
    (class Attachment extends Record {
        static id = "id";
        id;
    }).register(localRegistry);
    (class Thread extends Record {
        static id = AND("model", "id");
        id;
        model;
        attachments = fields.Many("Attachment");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert({ id: 1, model: "discuss.channel", attachments: [] });
    store.insert({
        Thread: {
            id: 1,
            model: "discuss.channel",
            attachments: [["REPLACE", [1774]]],
            __version__: "2026-08-01T00:00:10.000000",
        },
    });
    expect(thread.attachments.map(({ id }) => id)).toEqual([1774]);
    store.insert({
        Thread: {
            id: 1,
            model: "discuss.channel",
            attachments: [["ADD", [1775], "2026-08-01T00:00:20.000000"]],
        },
    });
    expect(thread.attachments.map(({ id }) => id)).toEqual([1774, 1775]);
    // Out of order, so the history gets reconciled: this is where the duplicate used to appear.
    store.insert({
        Thread: {
            id: 1,
            model: "discuss.channel",
            attachments: [["ADD", [1774], "2026-08-01T00:00:15.000000"]],
        },
    });
    expect(thread.attachments.map(({ id }) => id)).toEqual([1774, 1775], {
        message: "the attachment already present should not be duplicated",
    });
});

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
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([1, 2]);
    expect(store.Message.get(1).thread.id).toBe(1);
    store.insert({
        Thread: {
            id: 1,
            messages: [["DELETE", [{ id: 1, __version__: "2026-08-01T00:00:03.000000" }]]],
        },
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2]);
    expect(store.Message.get(1).thread).toBe(undefined);
    // Outdated update on the one side, shouldn't update the relation.
    store.insert({
        Message: { id: 1, thread: 1, __version__: "2026-08-01T00:00:02.000000" },
    });
    expect(store.Message.get(1).thread).toBe(undefined);
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2]);
    store.insert({
        Message: { id: 1, thread: 1, __version__: "2026-08-01T00:00:04.000000" },
    });
    expect(store.Message.get(1).thread.id).toBe(1);
    expect(
        store.Thread.get(1)
            .messages.map((m) => m.id)
            .sort()
    ).toEqual([1, 2]);
    // Outdated delete on the many side, shouldn't impact the relation.
    store.insert({
        Thread: {
            id: 1,
            messages: [["DELETE", [{ id: 1, __version__: "2026-08-01T00:00:03.000000" }]]],
        },
    });
    expect(
        store.Thread.get(1)
            .messages.map((m) => m.id)
            .sort()
    ).toEqual([1, 2]);
    expect(store.Message.get(1).thread.id).toBe(1);
});

test("a batched ADD echoes each item's own version onto its inverse, not the batch's latest", async () => {
    (class Message extends Record {
        static id = "id";
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);

    (class Thread extends Record {
        static id = "id";
        messages = fields.Many("Message", { inverse: "thread" });
    }).register(localRegistry);

    const store = await start();
    store.insert({
        Message: { id: 1, thread: 5, __version__: "2026-08-01T00:00:01.000000" },
    });
    store.insert({
        Thread: {
            id: 1,
            messages: [
                [
                    "ADD",
                    [
                        { id: 1, __version__: "2026-08-01T00:00:10.000000" },
                        { id: 2, __version__: "2026-08-01T00:00:20.000000" },
                    ],
                ],
            ],
        },
    });
    expect(store.Message.get(1).thread.id).toBe(1);
    // Older than message 2's version (which must not have been used for message 1), but
    // newer than message 1's own version, so it should apply.
    store.insert({
        Message: { id: 1, thread: 5, __version__: "2026-08-01T00:00:15.000000" },
    });
    expect(store.Message.get(1).thread.id).toBe(5);
});
