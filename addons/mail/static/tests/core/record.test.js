import { describe, afterEach, beforeAll, beforeEach, expect, test } from "@odoo/hoot";

import { BaseStore, Record, makeStore } from "@mail/core/common/record";

import { registry } from "@web/core/registry";
import { markup, reactive, toRaw } from "@odoo/owl";
import { mockService } from "@web/../tests/web_test_helpers";
import { Markup } from "@web/../lib/hoot/hoot_utils";
import { Matchers } from "@web/../lib/hoot/core/expect";
import { assertSteps, defineMailModels, start as start2, step } from "../mail_test_helpers";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";

describe.current.tags("desktop");
defineMailModels();

beforeAll(() => {
    if (!Matchers.registry["toRecEq"]) {
        expect.extend(function toRecEq(expected, options) {
            return {
                name: "toRecEq",
                acceptedType: "any",
                predicate: (actual) => actual?.eq(expected),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? `received value is[! not] record equal to %actual%`
                        : `expected values to be record equal`),
                details: (actual) => {
                    const details = [
                        [Markup.green("Expected:"), expected?.localId],
                        [Markup.red("Received:"), actual?.localId],
                    ];
                    details.push([
                        Markup.text("Diff:"),
                        Markup.diff(expected?.localId, actual?.localId),
                    ]);
                    return details;
                },
            };
        });
    }
    if (!Matchers.registry["toRecIn"]) {
        expect.extend(function toRecIn(reclist, options) {
            return {
                name: "toRecIn",
                acceptedType: "any",
                predicate: (record) => {
                    return record?.in(reclist);
                },
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? `received record is[! not] in record list`
                        : `expected record to be in record list`),
                details: (record) => {
                    const details = [
                        [Markup.green("Expected in reclist:"), record?.localId],
                        [Markup.red("Record list contains:"), reclist.map((rec) => rec.localId)],
                    ];
                    return details;
                },
            };
        });
    }
});

const localRegistry = registry.category("discuss.model.test");

beforeEach(() => {
    Record.register(localRegistry);
    ({ Store: class extends BaseStore {} }).Store.register(localRegistry);
    mockService("store", () => makeStore(getMockEnv(), { localRegistry }));
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

test("Insert by passing only single-id value (non-relational)", async () => {
    (class Persona extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const john = store.Persona.insert("John");
    expect(john.name).toBe("John");
});

test("Can pass object as data for relational field with inverse as id", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        composer = Record.one("Composer", { inverse: "thread" });
    }).register(localRegistry);
    (class Composer extends Record {
        static id = "thread";
        thread = Record.one("Thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    Object.assign(thread, { composer: {} });
    expect(thread.composer).toBeTruthy();
    expect(thread.composer.thread).toRecEq(thread);
});

test("Assign & Delete on fields with inverses", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        composer = Record.one("Composer", { inverse: "thread" });
        members = Record.many("Member", { inverse: "thread" });
        messages = Record.many("Message", { inverse: "threads" });
    }).register(localRegistry);
    (class Composer extends Record {
        static id = "thread";
        thread = Record.one("Thread");
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        thread = Record.one("Thread");
    }).register(localRegistry);
    (class Message extends Record {
        static id = "content";
        content;
        threads = Record.many("Thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const [john, marc] = store.Member.insert(["John", "Marc"]);
    const [hello, world] = store.Message.insert(["hello", "world"]);
    // Assign on fields should adapt inverses
    Object.assign(thread, { composer: {}, members: [["ADD", john]], messages: [hello, world] });
    expect(thread.composer).toBeTruthy();
    expect(thread.composer.thread).toRecEq(thread);
    expect(john.thread).toRecEq(thread);
    expect(john).toRecIn(thread.members);
    expect(hello).toRecIn(thread.messages);
    expect(world).toRecIn(thread.messages);
    expect(thread).toRecIn(hello.threads);
    expect(thread).toRecIn(world.threads);
    // add() should adapt inverses
    thread.members.add(marc);
    expect(marc).toRecIn(thread.members);
    expect(marc.thread).toRecEq(thread);
    // delete should adapt inverses
    thread.members.delete(john);
    expect(john).not.toRecIn(thread.members);
    expect(john.thread).not.toBeTruthy();
    // can delete with command
    thread.messages = [["DELETE", world]];
    expect(world).not.toRecIn(thread.messages);
    expect(thread).not.toRecIn(world.threads);
    expect(thread.messages.length).toBe(1);
    expect(hello).toRecIn(thread.messages);
    expect(thread).toRecIn(hello.threads);
    // Deletion removes all relations
    const composer = thread.composer;
    thread.delete();
    expect(thread.composer).not.toBeTruthy();
    expect(composer.thread).not.toBeTruthy();
    expect(marc).not.toRecIn(thread.members);
    expect(thread.members).toBeEmpty();
    expect(hello).not.toRecIn(thread.messages);
    expect(thread).not.toRecIn(hello.threads);
    expect(thread.messages).toBeEmpty();
});

test("onAdd/onDelete hooks on relational with inverse", async () => {
    let logs = [];
    (class Thread extends Record {
        static id = "name";
        name;
        members = Record.many("Member", {
            inverse: "thread",
            onAdd: (member) => logs.push(`Thread.onAdd(${member.name})`),
            onDelete: (member) => logs.push(`Thread.onDelete(${member.name})`),
        });
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        thread = Record.one("Thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const [john, marc] = store.Member.insert(["John", "Marc"]);
    thread.members.add(john);
    expect(logs).toEqual(["Thread.onAdd(John)"]);
    logs = [];
    thread.members.add(john);
    expect(logs).toBeEmpty();
    marc.thread = thread;
    expect(logs).toEqual(["Thread.onAdd(Marc)"]);
    logs = [];
    thread.members.delete(marc);
    expect(logs).toEqual(["Thread.onDelete(Marc)"]);
    logs = [];
    thread.members.delete(marc);
    expect(logs).toBeEmpty();
    john.thread = undefined;
    expect(logs).toEqual(["Thread.onDelete(John)"]);
});

test("Computed fields", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        type = Record.attr("", {
            compute() {
                if (this.members.length === 0) {
                    return "empty chat";
                } else if (this.members.length === 1) {
                    return "self-chat";
                } else if (this.members.length === 2) {
                    return "dm chat";
                } else {
                    return "group chat";
                }
            },
        });
        admin = Record.one("Persona", {
            compute() {
                return this.members[0];
            },
        });
        members = Record.many("Persona");
    }).register(localRegistry);
    (class Persona extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const [john, marc, antony] = store.Persona.insert(["John", "Marc", "Antony"]);
    Object.assign(thread, { members: [john, marc] });
    expect(thread.admin).toRecEq(john);
    expect(thread.type).toBe("dm chat");
    thread.members.delete(john);
    expect(thread.admin).toRecEq(marc);
    expect(thread.type).toBe("self-chat");
    thread.members.unshift(antony, john);
    expect(thread.admin).toRecEq(antony);
    expect(thread.type).toBe("group chat");
});

test("Computed fields: lazy (default) vs. eager", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        computeType() {
            if (this.members.length === 0) {
                return "empty chat";
            } else if (this.members.length === 1) {
                return "self-chat";
            } else if (this.members.length === 2) {
                return "dm chat";
            } else {
                return "group chat";
            }
        }
        typeLazy = Record.attr("", {
            compute() {
                expect.step("LAZY");
                return this.computeType();
            },
        });
        typeEager = Record.attr("", {
            compute() {
                expect.step("EAGER");
                return this.computeType();
            },
            eager: true,
        });
        members = Record.many("Persona");
    }).register(localRegistry);
    (class Persona extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const members = thread.members;
    expect(["EAGER"]).toVerifySteps();
    expect(thread.typeEager).toBe("empty chat");
    expect([]).toVerifySteps();
    expect(thread.typeLazy).toBe("empty chat");
    expect(["LAZY"]).toVerifySteps();
    members.add("John");
    expect(["EAGER"]).toVerifySteps();
    expect(thread.typeEager).toBe("self-chat");
    expect([]).toVerifySteps();
    members.add("Antony");
    expect(["EAGER"]).toVerifySteps();
    expect(thread.typeEager).toBe("dm chat");
    expect([]).toVerifySteps();
    members.add("Demo");
    expect(["EAGER"]).toVerifySteps();
    expect(thread.typeEager).toBe("group chat");
    expect(thread.typeLazy).toBe("group chat");
    expect(["LAZY"]).toVerifySteps();
});

test("Trusted insert on html field with { html: true }", async () => {
    (class Message extends Record {
        static id = "body";
        body = Record.attr("", { html: true });
    }).register(localRegistry);
    const store = await start();
    const hello = store.Message.insert("<p>hello</p>", { html: true });
    const world = store.Message.insert("<p>world</p>");
    expect(hello.body instanceof markup("").constructor).toBeTruthy();
    expect(hello.body.toString()).toBe("<p>hello</p>");
    expect(world.body).toBe("<p>world</p>");
});

test("(Un)trusted insertion is applied even with same field value", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        body = Record.attr("", { html: true });
    }).register(localRegistry);
    const store = await start();
    const rawMessage = { id: 1, body: "<p>hello</p>" };
    let message = store.Message.insert(rawMessage);
    expect(message.body instanceof markup("").constructor).not.toBeTruthy();
    message = store.Message.insert(rawMessage, { html: true });
    expect(message.body instanceof markup("").constructor).toBeTruthy();
    message = store.Message.insert(rawMessage);
    expect(message.body instanceof markup("").constructor).not.toBeTruthy();
});

test("Unshift preserves order", async () => {
    (class Message extends Record {
        static id = "id";
        id;
    }).register(localRegistry);
    (class Thread extends Record {
        static id = "name";
        name;
        messages = Record.many("Message");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert({ name: "General" });
    thread.messages.unshift({ id: 3 }, { id: 2 }, { id: 1 });
    expect(thread.messages.map((msg) => msg.id)).toEqual([3, 2, 1]);
    thread.messages.unshift({ id: 6 }, { id: 5 }, { id: 4 });
    expect(thread.messages.map((msg) => msg.id)).toEqual([6, 5, 4, 3, 2, 1]);
    thread.messages.unshift({ id: 7 });
    expect(thread.messages.map((msg) => msg.id)).toEqual([7, 6, 5, 4, 3, 2, 1]);
});

test("onAdd hook should see fully inserted data", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = Record.many("Member", {
            inverse: "thread",
            onAdd: (member) =>
                expect.step(`Thread.onAdd::${member.name}.${member.type}.${member.isAdmin}`),
        });
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        type;
        isAdmin = Record.attr(false, {
            compute() {
                return this.type === "admin";
            },
        });
        thread = Record.one("Thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    thread.members.add({ name: "John", type: "admin" });
    expect(["Thread.onAdd::John.admin.true"]).toVerifySteps();
});

test("Can insert with relation as id, using relation as data object", async () => {
    (class User extends Record {
        static id = "name";
        name;
        settings = Record.one("Settings");
    }).register(localRegistry);
    (class Settings extends Record {
        static id = "user";
        pushNotif;
        user = Record.one("User", { inverse: "settings" });
    }).register(localRegistry);
    const store = await start();
    store.Settings.insert([
        { pushNotif: true, user: { name: "John" } },
        { pushNotif: false, user: { name: "Paul" } },
    ]);
    expect(store.User.get("John")).toBeTruthy();
    expect(store.User.get("John").settings.pushNotif).toBeTruthy();
    expect(store.User.get("Paul")).toBeTruthy();
    expect(store.User.get("Paul").settings.pushNotif).not.toBeTruthy();
});

test("Set on attr should invoke onChange", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        body;
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert(1);
    Record.onChange(message, "body", () => expect.step("BODY_CHANGED"));
    expect([]).toVerifySteps();
    message.update({ body: "test1" });
    message.body = "test2";
    expect(["BODY_CHANGED", "BODY_CHANGED"]).toVerifySteps();
});

test("record list sort should be manually observable", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        messages = Record.many("Message", { inverse: "thread" });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        body;
        author;
        thread = Record.one("Thread", { inverse: "messages" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert(1);
    const messages = store.Message.insert([
        { id: 1, body: "a", thread },
        { id: 2, body: "b", thread },
    ]);
    function sortMessages() {
        // minimal access through observed variables to reduce unexpected observing
        observedMessages.sort((m1, m2) => (m1.body < m2.body ? -1 : 1));
        expect.step(`sortMessages`);
    }
    const observedMessages = reactive(thread.messages, sortMessages);
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    sortMessages();
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    expect(["sortMessages"]).toVerifySteps();
    messages[0].body = "c";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    expect(["sortMessages", "sortMessages"]).toVerifySteps();
    messages[0].body = "d";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    expect(["sortMessages"]).toVerifySteps();
    messages[0].author = "Jane";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    expect([]).toVerifySteps();
    store.Message.insert({ id: 3, body: "c", thread });
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,3,1");
    expect(["sortMessages", "sortMessages"]).toVerifySteps();
    messages[0].delete();
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,3");
    expect(["sortMessages"]).toVerifySteps();
});

test("relation field sort should be automatically observed", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        messages = Record.many("Message", {
            inverse: "thread",
            sort: (m1, m2) => (m1.body < m2.body ? -1 : 1),
        });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        body;
        author;
        thread = Record.one("Thread", { inverse: "messages" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert(1);
    const messages = store.Message.insert([
        { id: 1, body: "a", thread },
        { id: 2, body: "b", thread },
    ]);
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    messages[0].body = "c";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    messages[0].body = "d";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    messages[0].author = "Jane";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    store.Message.insert({ id: 3, body: "c", thread });
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,3,1");
    messages[0].delete();
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,3");
});

test("reading of lazy compute relation field should recompute", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        messages = Record.many("Message", {
            inverse: "thread",
            sort: (m1, m2) => (m1.body < m2.body ? -1 : 1),
        });
        messages2 = Record.many("Message", {
            compute() {
                return this.messages.map((m) => m.id);
            },
        });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        thread = Record.one("Thread", { inverse: "messages" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert(1);
    store.Message.insert([
        { id: 1, thread },
        { id: 2, thread },
    ]);
    const messages2 = thread.messages2;
    expect(`${messages2.map((m) => m.id)}`).toBe("1,2");
    store.Message.insert([{ id: 3, thread }]);
    expect(`${messages2.map((m) => m.id)}`).toBe("1,2,3");
    store.Message.insert([{ id: 4, thread }]);
    expect(`${messages2.map((m) => m.id)}`).toBe("1,2,3,4");
});

test("lazy compute should re-compute while they are observed", async () => {
    (class Channel extends Record {
        static id = "id";
        id;
        count = 0;
        multiplicity = Record.attr(undefined, {
            compute() {
                expect.step("computing");
                if (this.count > 3) {
                    return "many";
                }
                return "few";
            },
        });
    }).register(localRegistry);
    const store = await start();
    const channel = store.Channel.insert(1);
    let observe = true;
    function render() {
        if (observe) {
            expect.step(`render ${reactiveChannel.multiplicity}`);
        }
    }
    const reactiveChannel = reactive(channel, render);
    render();
    expect(["computing", "render few", "render few"]).toVerifySteps({
        message: "initial call, render with new value",
    });
    channel.count = 2;
    expect(["computing"]).toVerifySteps({ message: "changing value to 2 is observed" });
    channel.count = 5;
    expect(["computing", "render many"]).toVerifySteps({
        message: "changing value to 5 is observed",
    });
    observe = false;
    channel.count = 6;
    expect(["computing"]).toVerifySteps({
        message: "changing value to 6, still observed until it changes",
    });
    channel.count = 7;
    expect(["computing"]).toVerifySteps({
        message: "changing value to 7, still observed until it changes",
    });
    channel.count = 1;
    expect(["computing"]).toVerifySteps({ message: "changing value to 1, observed one last time" });
    channel.count = 0;
    expect([]).toVerifySteps({ message: "changing value to 0, no longer observed" });
    channel.count = 7;
    expect([]).toVerifySteps({ message: "changing value to 7, no longer observed" });
    channel.count = 1;
    expect([]).toVerifySteps({ message: "changing value to 1, no longer observed" });
    expect(channel.multiplicity).toBe("few");
    expect(["computing"]).toVerifySteps();
    observe = true;
    render();
    expect(["render few"]).toVerifySteps();
    channel.count = 7;
    expect(["computing", "render many"]).toVerifySteps();
});

test("lazy sort should re-sort while they are observed", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        messages = Record.many("Message", {
            sort: (m1, m2) => m1.sequence - m2.sequence,
        });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        sequence;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert(1);
    thread.messages.push({ id: 1, sequence: 1 }, { id: 2, sequence: 2 });
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    let observe = true;
    function render() {
        if (observe) {
            expect.step(`render ${reactiveChannel.messages.map((m) => m.id)}`);
        }
    }
    const reactiveChannel = reactive(thread, render);
    render();
    const message = thread.messages[0];
    expect(["render 1,2"]).toVerifySteps();
    message.sequence = 3;
    expect(["render 2,1"]).toVerifySteps();
    message.sequence = 4;
    expect([]).toVerifySteps();
    message.sequence = 5;
    expect([]).toVerifySteps();
    message.sequence = 1;
    expect(["render 1,2"]).toVerifySteps();
    observe = false;
    message.sequence = 10;
    expect(
        `${toRaw(thread)
            ._raw._fields.get("messages")
            .value.data.map((localId) => toRaw(thread)._raw._store.get(localId).id)}`
    ).toBe("2,1", { message: "observed one last time when it changes" });
    expect([]).toVerifySteps();
    message.sequence = 1;
    expect(
        `${toRaw(thread)
            ._raw._fields.get("messages")
            .value.data.map((localId) => toRaw(thread)._raw._store.get(localId).id)}`
    ).toBe("2,1", { message: "no longer observed" });
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    observe = true;
    render();
    expect(["render 1,2"]).toVerifySteps();
    message.sequence = 10;
    expect(["render 2,1"]).toVerifySteps();
});

test("store updates can be observed", async () => {
    const store = await start();
    function onUpdate() {
        expect.step(`abc:${reactiveStore.abc}`);
    }
    const rawStore = toRaw(store)._raw;
    const reactiveStore = reactive(store, onUpdate);
    onUpdate();
    expect(["abc:undefined"]).toVerifySteps();
    store.abc = 1;
    expect(["abc:1"]).toVerifySteps({ message: "observable from makeStore" });
    rawStore._store.abc = 2;
    expect(["abc:2"]).toVerifySteps({ message: "observable from record._store" });
    rawStore.Model.store.abc = 3;
    expect(["abc:3"]).toVerifySteps({ message: "observable from Model.store" });
});

test("onAdd/onDelete hooks on one without inverse", async () => {
    (class Thread extends Record {
        static id = "name";
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        thread = Record.one("Thread", {
            onAdd: (thread) => step(`thread.onAdd(${thread.name})`),
            onDelete: (thread) => step(`thread.onDelete(${thread.name})`),
        });
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    const john = store.Member.insert("John");
    await assertSteps([]);
    john.thread = general;
    await assertSteps(["thread.onAdd(General)"]);
    john.thread = general;
    await assertSteps([]);
    john.thread = undefined;
    await assertSteps(["thread.onDelete(General)"]);
});

test("onAdd/onDelete hooks on many without inverse", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = Record.many("Member", {
            onAdd: (member) => step(`members.onAdd(${member.name})`),
            onDelete: (member) => step(`members.onDelete(${member.name})`),
        });
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    const jane = store.Member.insert("Jane");
    const john = store.Member.insert("John");
    await assertSteps([]);
    general.members = jane;
    await assertSteps(["members.onAdd(Jane)"]);
    general.members = jane;
    await assertSteps([]);
    general.members = [["ADD", john]];
    await assertSteps(["members.onAdd(John)"]);
    general.members = undefined;
    await assertSteps(["members.onDelete(John)", "members.onDelete(Jane)"]);
});

test("record list assign should update inverse fields", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = Record.many("Member", { inverse: "thread" });
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        thread = Record.one("Thread", { inverse: "members" });
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    const jane = store.Member.insert("Jane");
    general.members = jane; // direct assignation of value goes through assign()
    expect(jane.thread).toRecEq(general);
    general.members = []; // writing empty array specifically goes through assign()
    expect(jane.thread).not.toBeTruthy();
    jane.thread = general;
    expect(jane).toRecIn(general.members);
    jane.thread = [];
    expect(jane).not.toRecIn(general.members);
});

test("datetime type record", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        date = Record.attr(undefined, {
            type: "datetime",
            onUpdate: () => step("DATE_UPDATED"),
        });
    }).register(localRegistry);
    const store = await start();
    await assertSteps([]);
    const general = store.Thread.insert({ name: "General", date: "2024-02-20 14:42:00" });
    await assertSteps(["DATE_UPDATED"]);
    expect(general.date instanceof luxon.DateTime).toBeTruthy();
    expect(general.date.day).toBe(20);
    store.Thread.insert({ name: "General", date: "2024-02-21 14:42:00" });
    await assertSteps(["DATE_UPDATED"]);
    expect(general.date.day).toBe(21);
    store.Thread.insert({ name: "General", date: "2024-02-21 14:42:00" });
    await assertSteps([]);
    store.Thread.insert({ name: "General", date: undefined });
    await assertSteps(["DATE_UPDATED"]);
    expect(general.date).toBe(undefined);
    const now = luxon.DateTime.now();
    const thread = store.Thread.insert({ name: "General", date: now });
    await assertSteps(["DATE_UPDATED"]);
    expect(thread.date instanceof luxon.DateTime).toBeTruthy();
    expect(thread.date.equals(now)).toBeTruthy();
    store.Thread.insert({ name: "General", date: false });
    await assertSteps(["DATE_UPDATED"]);
    expect(general.date).toBe(false);
    store.Thread.insert({ name: "General", date: "2024-02-22 14:42:00" });
    await assertSteps(["DATE_UPDATED"]);
    expect(general.date.day).toBe(22);
});
