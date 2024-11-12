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
        "mail.link.preview": [{ id: 1, message_id: { id: 1 } }],
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

    const { Thread: threads } = store.insert(data);
    expect(threads).toHaveLength(3);
    const general = store.Thread.get({ id: 1, model: "discuss.channel" });
    const sales = store.Thread.get({ id: 2, model: "discuss.channel" });
    const rd = store.Thread.get({ id: 3, model: "discuss.channel" });
    expect(general.in(threads)).toBe(true);
    expect(sales.in(threads)).toBe(true);
    expect(rd.in(threads)).toBe(true);
});
