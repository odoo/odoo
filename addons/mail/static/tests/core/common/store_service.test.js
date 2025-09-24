import { Message } from "@mail/core/common/message_model";

import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";

import { expect, test } from "@odoo/hoot";

import {
    asyncStep,
    getService,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

defineMailModels();

test("store.insert can delete record", async () => {
    await start();
    const store = getService("mail.store");
    store.insert({ "mail.message": [{ id: 1 }] });
    expect(store["mail.message"].get({ id: 1 })?.id).toBe(1);
    store.insert({ "mail.message": [{ id: 1, _DELETE: true }] });
    expect(store["mail.message"].get({ id: 1 })?.id).toBe(undefined);
});

test("store.insert deletes record without creating it", async () => {
    patchWithCleanup(Message, {
        new() {
            const message = super.new(...arguments);
            asyncStep(`new-${message.id}`);
            return message;
        },
    });
    await start();
    const store = getService("mail.store");
    store.insert({ "mail.message": [{ id: 1, _DELETE: true }] });
    await waitForSteps([]);
    expect(store["mail.message"].get({ id: 1 })?.id).toBe(undefined);
    store.insert({ "mail.message": [{ id: 2 }] });
    await waitForSteps(["new-2"]);
});

test("store.insert deletes record after relation created it", async () => {
    patchWithCleanup(Message, {
        new() {
            const message = super.new(...arguments);
            asyncStep(`new-${message.id}`);
            return message;
        },
    });
    await start();
    const store = getService("mail.store");
    store.insert({
        "mail.message": [{ id: 1, _DELETE: true }],
        // they key coverage of the test is to have the relation listed after the delete
        "mail.link.preview": [{ id: 1 }],
        "mail.message.link.preview": [{ id: 1, link_preview_id: 1, message_id: 1 }],
    });
    await waitForSteps(["new-1"]);
    expect(store["mail.message"].get({ id: 1 })?.id).toBe(undefined);
});

test("store.insert different PY model having same JS model", async () => {
    await start();
    const store = getService("mail.store");
    const data = {
        "discuss.channel": [
            { id: 1, name: "General" },
            { id: 2, name: "Sales" },
        ],
        "mail.thread": [
            { id: 1, model: "discuss.channel" },
            { id: 3, name: "R&D", model: "discuss.channel" },
        ],
    };

    store.insert(data);
    expect(store.Thread.records).toHaveLength(6); // 3 mailboxes + 3 channels
    expect(Boolean(store.Thread.get({ id: 1, model: "discuss.channel" }))).toBe(true);
    expect(Boolean(store.Thread.get({ id: 2, model: "discuss.channel" }))).toBe(true);
    expect(Boolean(store.Thread.get({ id: 3, model: "discuss.channel" }))).toBe(true);
});

test("store.insert uses version for overrides", async () => {
    await start();
    const store = getService("mail.store");
    store.insert({
        "mail.message": [{ id: 1, subject: "version 1", version: 1 }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 1");
    store.insert({
        "mail.message": [{ id: 1, subject: "version 2", version: 2 }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 2");
    store.insert({
        "mail.message": [{ id: 1, subject: "version 1", version: 1 }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 2");
});

test("store.insert uses version for many relations", async () => {
    await start();
    const store = getService("mail.store");
    store.insert({
        "mail.message": [{ id: 1, subject: "version 1", version: 1, partner_ids: [1] }],
        "res.partner": [
            { id: 1, name: "Partner 1" },
            { id: 2, name: "Partner 2" },
            { id: 3, name: "Partner 3" },
        ],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 1");
    expect(store["mail.message"].get({ id: 1 })?.partner_ids.map((p) => p.name)).toEqual([
        "Partner 1",
    ]);
    store.insert({
        "mail.message": [{ id: 1, subject: "version 4", version: 4, partner_ids: [["ADD", 2]] }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 4");
    expect(store["mail.message"].get({ id: 1 })?.partner_ids.map((p) => p.name)).toEqual([
        "Partner 1",
        "Partner 2",
    ]);
    store.insert({
        "mail.message": [{ id: 1, version: 2, partner_ids: [3] }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 4");
    expect(store["mail.message"].get({ id: 1 })?.partner_ids.map((p) => p.name)).toEqual([
        "Partner 3",
        "Partner 2",
    ]);
    store.insert({
        "mail.message": [{ id: 1, version: 4, partner_ids: [1, 2, 3] }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 4");
    expect(store["mail.message"].get({ id: 1 })?.partner_ids.map((p) => p.name)).toEqual([
        "Partner 1",
        "Partner 2",
        "Partner 3",
    ]);
    store.insert({
        "res.partner": [{ id: 2, name: "Partner 2 (updated)", version: 2 }],
    });
    expect(store["mail.message"].get({ id: 1 })?.partner_ids.map((p) => p.name)).toEqual([
        "Partner 1",
        "Partner 2 (updated)",
        "Partner 3",
    ]);
});

test("store.insert uses version for one relations", async () => {
    await start();
    const store = getService("mail.store");
    store.insert({
        "mail.message": [{ id: 1, subject: "version 1", version: 1, author_id: 1 }],
        "res.partner": [
            { id: 1, name: "Partner 1" },
            { id: 2, name: "Partner 2" },
            { id: 3, name: "Partner 3" },
        ],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 1");
    expect(store["mail.message"].get({ id: 1 })?.author_id.name).toBe("Partner 1");
    store.insert({
        "mail.message": [{ id: 1, subject: "version 4", version: 4, author_id: 2 }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 4");
    expect(store["mail.message"].get({ id: 1 })?.author_id.name).toBe("Partner 2");
    store.insert({
        "mail.message": [{ id: 1, version: 2, author_id: 3 }],
    });
    expect(store["mail.message"].get({ id: 1 })?.subject).toBe("version 4");
    expect(store["mail.message"].get({ id: 1 })?.author_id.name).toBe("Partner 2");
});
