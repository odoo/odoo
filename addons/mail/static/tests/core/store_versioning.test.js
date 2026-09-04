import { AND, fields, makeStore, Record, Store } from "@mail/model/export";
import { defineMailModels, start as start2 } from "@mail/../tests/mail_test_helpers";

import { afterEach, beforeEach, expect, test } from "@odoo/hoot";

import { registry } from "@web/core/registry";
import { mockService } from "@web/../tests/web_test_helpers";

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
        name: "keep incoming record if it comes from a newer version",
        initial: { id: 1, name: "v0" },
        steps: [
            {
                values: { name: "v1", __version__: "2026-01-01T00:00:10.000000" },
                expected: { name: "v1" },
            },
            {
                values: { name: "v3", __version__: "2026-01-01T00:00:40.000000" },
                expected: { name: "v3" },
                description: "V3's version is newer.",
            },
            {
                values: { name: "v2", __version__: "2026-01-01T00:00:30.000000" },
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
                    __version__: "2026-01-01T00:00:10.000000",
                },
                expected: { name: "v1", description: "desc1" },
            },
            {
                values: { name: "v3", __version__: "2026-01-01T00:00:30.000000" },
                expected: { name: "v3", description: "desc1" },
            },
            {
                values: {
                    name: "v2",
                    description: "desc2",
                    __version__: "2026-01-01T00:00:20.000000",
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
                values: { name: "v2", __version__: "2026-01-01T00:00:10.000000" },
                expected: { name: "v2" },
            },
            {
                values: { name: "v1", __version__: "2026-01-01T00:00:05.000000" },
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
                values: { name: "v2", __version__: "2026-01-01T00:00:10.123999" },
                expected: { name: "v2" },
            },
            {
                values: { name: "v1", __version__: "2026-01-01T00:00:10.123456" },
                expected: { name: "v2" },
                description:
                    "v1 is chronologically older than v2 (same millisecond, earlier " +
                    "microsecond); a millisecond-only comparison would see them as equal " +
                    "and let v1 win by arrival order instead.",
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
        console.clear();
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
        name: "keep incoming replace even if it comes from an older replace",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: {
                    messages: [["REPLACE", [1, 2, 3]]],
                    __version__: "2026-01-01T00:00:10.000000",
                },
                expected: [1, 2, 3],
            },
            {
                values: {
                    messages: [["REPLACE", [7, 8, 9]]],
                    __version__: "2026-01-01T00:00:30.000000",
                },
                expected: [7, 8, 9],
            },
            {
                values: {
                    messages: [["REPLACE", [4, 5, 6]]],
                    __version__: "2026-01-01T00:00:20.000000",
                },
                expected: [4, 5, 6],
                description: "Replace is outdated thus applied.",
            },
        ],
    },
    {
        name: "keep incoming commands if it comes after the base replace",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: {
                    messages: [["REPLACE", [1, 2, 3]]],
                    __version__: "2026-01-01T00:00:20.000000",
                },
                expected: [1, 2, 3],
            },
            {
                values: { messages: [["ADD", [7, 8]]], __version__: "2026-01-01T00:00:30.000000" },
                expected: [1, 2, 3, 7, 8],
            },
            {
                values: {
                    messages: [["DELETE", [7, 8]]],
                    __version__: "2026-01-01T00:00:40.000000",
                },
                expected: [1, 2, 3],
            },
            {
                values: {
                    messages: [["DELETE", [1, 2, 3]]],
                    __version__: "2026-01-01T00:00:15.000000",
                },
                expected: [],
                description:
                    "Delete command comes from an older version than the base replace, but the " +
                    "base replace is unversioned: applied anyway.",
            },
        ],
    },
    {
        name: "commands arriving out of order are properly handled",
        initial: { id: 1, messages: [1, 2, 3] },
        steps: [
            {
                values: {
                    messages: [["ADD", [4, 5, 6]]],
                    __version__: "2026-01-01T00:00:20.000000",
                },
                expected: [1, 2, 3, 4, 5, 6],
            },
            {
                values: {
                    messages: [["DELETE", [1, 4]]],
                    __version__: "2026-01-01T00:00:15.000000",
                },
                expected: [2, 3, 4, 5, 6],
                description: "4 was added after the delete command, but 1 wasn't.",
            },
        ],
    },
    {
        name: "newer commands arriving before replace are not kept",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: { messages: [["REPLACE", []]], __version__: "2026-01-01T00:00:10.000000" },
                expected: [],
            },
            {
                values: {
                    messages: [["ADD", [4, 5, 6]]],
                    __version__: "2026-01-01T00:00:20.000000",
                },
                expected: [4, 5, 6],
            },
            {
                values: { messages: [["REPLACE", [1]]], __version__: "2026-01-01T00:00:15.000000" },
                expected: [1],
                description:
                    "Replace came before the ADD, even if it was received after: add is not kept.",
            },
        ],
    },
    {
        name: "keep command with equivalent version as the last replace when they come after it",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: {
                    messages: [["REPLACE", [1, 2, 3]]],
                    __version__: "2026-01-01T00:00:10.000000",
                },
                expected: [1, 2, 3],
            },
            {
                values: {
                    messages: [["ADD", [4, 5, 6]]],
                    __version__: "2026-01-01T00:00:10.000000",
                },
                expected: [1, 2, 3, 4, 5, 6],
            },
        ],
    },
    {
        name: "an ADD's own version takes precedence over the record's",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: {
                    messages: [["ADD", [2], "2026-01-01T00:00:10.000000"]],
                    __version__: "2026-01-01T00:00:50.000000",
                },
                expected: [2],
            },
            {
                values: { messages: [["DELETE", [2], "2026-01-01T00:00:30.000000"]] },
                expected: [],
                description:
                    "The add's own version (10) is older than the delete (30), so it is " +
                    "removed, even though the record's version on that same payload (50) " +
                    "was newer.",
            },
        ],
    },
    {
        name: "a link removed then added back out of order is kept",
        initial: { id: 1, messages: [] },
        steps: [
            {
                values: { messages: [["REPLACE", [7], "2026-01-01T00:00:10.000000"]] },
                expected: [7],
            },
            {
                values: { messages: [["DELETE", [7], "2026-01-01T00:00:30.000000"]] },
                expected: [],
            },
            {
                values: { messages: [["ADD", [7], "2026-01-01T00:00:60.000000"]] },
                expected: [7],
                description: "The link was added back after the deletion.",
            },
        ],
    },
    {
        name: "values within a single ADD command are versioned independently",
        initial: { id: 1, messages: [] },
        steps: [
            {
                // An ADD isn't necessarily emitted when a link is created: it can equally
                // come from a plain read re-serializing values added at different times
                // (e.g. a message's reactions, each added by a different user).
                values: {
                    messages: [
                        [
                            "ADD",
                            [
                                { id: 1, __version__: "2026-01-01T00:00:10.000000" },
                                { id: 2, __version__: "2026-01-01T00:00:30.000000" },
                            ],
                        ],
                    ],
                },
                expected: [1, 2],
            },
            {
                values: { messages: [["DELETE", [1], "2026-01-01T00:00:20.000000"]] },
                expected: [2],
                description:
                    "The delete (20) is older than message 2's add (30) but newer than " +
                    "message 1's (10): only message 1, actually added before the delete, " +
                    "is removed. Stamping the whole ADD as one command would have let the " +
                    "delete wrongly remove message 2 as well, or wrongly spare message 1.",
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
        Thread: { id: 1, messages: [["ADD", [6], "2026-01-01T00:00:30.000000"]] },
    });
    store.insert({
        Thread: { id: 1, messages: [["DELETE", [1], "2026-01-01T00:00:20.000000"]] },
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
        Message: { id: 1, thread: 9, __version__: "2026-01-01T00:00:30.000000" },
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
            __version__: "2026-01-01T00:00:10.000000",
        },
    });
    expect(thread.attachments.map(({ id }) => id)).toEqual([1774]);
    store.insert({
        Thread: {
            id: 1,
            model: "discuss.channel",
            attachments: [["ADD", [1775], "2026-01-01T00:00:20.000000"]],
        },
    });
    expect(thread.attachments.map(({ id }) => id)).toEqual([1774, 1775]);
    // Out of order, so the history gets reconciled: this is where the duplicate used to appear.
    store.insert({
        Thread: {
            id: 1,
            model: "discuss.channel",
            attachments: [["ADD", [1774], "2026-01-01T00:00:15.000000"]],
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
        Thread: {
            id: 1,
            messages: [["REPLACE", [1, 2]]],
            __version__: "2026-01-01T00:00:01.000000",
        },
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([1, 2]);
    expect(store.Message.get(1).thread.id).toBe(1);
    store.insert({
        Thread: { id: 1, messages: [["DELETE", [1]]], __version__: "2026-01-01T00:00:03.000000" },
    });
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2]);
    expect(store.Message.get(1).thread).toBe(undefined);
    // Outdated update on the one side, shouldn't update the relation.
    store.insert({
        Message: { id: 1, thread: 1, __version__: "2026-01-01T00:00:02.000000" },
    });
    expect(store.Message.get(1).thread).toBe(undefined);
    expect(store.Thread.get(1).messages.map((m) => m.id)).toEqual([2]);
    store.insert({
        Message: { id: 1, thread: 1, __version__: "2026-01-01T00:00:04.000000" },
    });
    expect(store.Message.get(1).thread.id).toBe(1);
    expect(
        store.Thread.get(1)
            .messages.map((m) => m.id)
            .sort()
    ).toEqual([1, 2]);
    // Outdated delete on the many side, shouldn't impact the relation.
    store.insert({
        Thread: { id: 1, messages: [["DELETE", [1]]], __version__: "2026-01-01T00:00:03.000000" },
    });
    expect(
        store.Thread.get(1)
            .messages.map((m) => m.id)
            .sort()
    ).toEqual([1, 2]);
    expect(store.Message.get(1).thread.id).toBe(1);
});
