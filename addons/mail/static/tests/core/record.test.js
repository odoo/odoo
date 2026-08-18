import { toRawValue } from "@mail/utils/common/local_storage";
import { defineMailModels, start as start2 } from "@mail/../tests/mail_test_helpers";
import { after, afterEach, beforeEach, describe, expect, test, tick } from "@odoo/hoot";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { Component, immediateEffect, markup, proxy, xml } from "@odoo/owl";
import {
    getService,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { Record, Store, makeStore } from "@mail/model/export";
import { AND, fields, makeRecordFieldLocalId, normalizeManyCommands } from "@mail/model/misc";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

const Markup = markup().constructor;

describe.current.tags("desktop");
defineMailModels();

const expectRecord = (record, not = false) => {
    const toBeIn = (reclist) => {
        expect(record?.in(reclist)).toBe(!not);
    };

    const toEqual = (expected) => {
        expect(record?.eq(expected)).toBe(!not);
    };

    return {
        get not() {
            return expectRecord(record, !not);
        },
        toBeIn,
        toEqual,
    };
};

const localRegistry = registry.category("discuss.model.test");

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
    /** @type {Store} */
    const store = getService("store");
    after(() => store._runDisposeFns());
    return store;
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
        composer = fields.One("Composer", { inverse: "thread" });
    }).register(localRegistry);
    (class Composer extends Record {
        static id = "thread";
        thread = fields.One("Thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    Object.assign(thread, { composer: {} });
    expectRecord(thread.composer.thread).toEqual(thread);
});

test("pass single-id as data for 'one' relational field without inverse", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        author = fields.One("Partner");
    }).register(localRegistry);
    (class Partner extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert({ id: 1, author: "John" });
    const author = message.author;
    expect(author.name).toBe("John");
    store.Message.insert({ id: 1, author: null });
    expect(message.author).toBe(undefined);
    expect(author.name).toBe("John");
    store.Message.insert({ id: 1, author: false });
    expect(message.author).toBe(undefined);
    store.Message.insert({ id: 1, author: undefined });
    expect(message.author).toBe(undefined);
});

test("pass single-id as data for 'one' relational field with inverse", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        author = fields.One("Partner", { inverse: "messages" });
    }).register(localRegistry);
    (class Partner extends Record {
        static id = "name";
        name;
        messages = fields.Many("Message", { inverse: "author" });
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert({ id: 1, author: "John" });
    const author = message.author;
    expect(author.name).toBe("John");
    expect(author.messages.length).toBe(1);
    expect(author.messages[0]).toBe(message);
    store.Message.insert({ id: 1, author: null });
    expect(message.author).toBe(undefined);
    expect(author.name).toBe("John");
    store.Message.insert({ id: 1, author: false });
    expect(message.author).toBe(undefined);
    store.Message.insert({ id: 1, author: undefined });
    expect(message.author).toBe(undefined);
});

test("pass single-id as data for 'one' relational field as id", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        composer = fields.One("Composer", { inverse: "thread" });
    }).register(localRegistry);
    (class Composer extends Record {
        static id = "thread";
        thread = fields.One("Thread", { inverse: "composer" });
        composerView = fields.Many("ComposerView", { inverse: "composer" });
    }).register(localRegistry);
    (class ComposerView extends Record {
        static id = "id";
        composer = fields.One("Composer", { inverse: "composerView" });
    }).register(localRegistry);
    const store = await start();
    const composerView = store.ComposerView.insert({ id: 1, composer: 2 });
    const composer = composerView.composer;
    expect(composer.thread.id).toBe(2);
    store.ComposerView.insert({ id: 1, composer: null });
    expect(composerView.composer).toBe(undefined);
    expect(composer.thread.id).toBe(2);
    store.ComposerView.insert({ id: 1, composer: false });
    expect(composerView.composer).toBe(undefined);
    store.ComposerView.insert({ id: 1, composer: undefined });
    expect(composerView.composer).toBe(undefined);
});

test("pass single-id as data for 'many' relational field without inverse", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        authors = fields.Many("Partner");
    }).register(localRegistry);
    (class Partner extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert({ id: 1, authors: ["John", "Jane"] });
    expect(message.authors.length).toBe(2);
    expect(message.authors[0].name).toBe("John");
    expect(message.authors[1].name).toBe("Jane");
});

test("pass single-id as data for 'many' relational field with inverse", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        authors = fields.Many("Partner", { inverse: "messages" });
    }).register(localRegistry);
    (class Partner extends Record {
        static id = "name";
        name;
        messages = fields.Many("Message", { inverse: "authors" });
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert({ id: 1, authors: ["John", "Jane"] });
    expect(message.authors.length).toBe(2);
    expect(message.authors[0].name).toBe("John");
    expect(message.authors[0].messages.length).toBe(1);
    expect(message.authors[0].messages[0]).toBe(message);
    expect(message.authors[1].name).toBe("Jane");
    expect(message.authors[1].messages.length).toBe(1);
    expect(message.authors[1].messages[0]).toBe(message);
});

test("Assign & Delete on fields with inverses", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        composer = fields.One("Composer", { inverse: "thread" });
        members = fields.Many("Member", { inverse: "thread" });
        messages = fields.Many("Message", { inverse: "threads" });
    }).register(localRegistry);
    (class Composer extends Record {
        static id = "thread";
        thread = fields.One("Thread");
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        thread = fields.One("Thread");
    }).register(localRegistry);
    (class Message extends Record {
        static id = "content";
        content;
        threads = fields.Many("Thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const [john, marc] = store.Member.insert(["John", "Marc"]);
    const [hello, world] = store.Message.insert(["hello", "world"]);
    // Assign on fields should adapt inverses
    Object.assign(thread, { composer: {}, members: [["ADD", john]], messages: [hello, world] });
    expectRecord(thread.composer.thread).toEqual(thread);
    expectRecord(john.thread).toEqual(thread);
    expectRecord(john).toBeIn(thread.members);
    expectRecord(hello).toBeIn(thread.messages);
    expectRecord(world).toBeIn(thread.messages);
    expectRecord(thread).toBeIn(hello.threads);
    expectRecord(thread).toBeIn(world.threads);
    // add() should adapt inverses
    thread.members.add(marc);
    expectRecord(marc).toBeIn(thread.members);
    expectRecord(marc.thread).toEqual(thread);
    // delete should adapt inverses
    thread.members.delete(john);
    expectRecord(john).not.toBeIn(thread.members);
    expect(Boolean(john.thread)).toBe(false);
    // can delete with command
    thread.messages = [["DELETE", world]];
    expectRecord(world).not.toBeIn(thread.messages);
    expectRecord(thread).not.toBeIn(world.threads);
    expect(thread.messages).toHaveLength(1);
    expectRecord(hello).toBeIn(thread.messages);
    expectRecord(thread).toBeIn(hello.threads);
    // Deletion removes all relations
    const composer = thread.composer;
    thread.delete();
    expect(Boolean(thread.composer)).toBe(false);
    expect(Boolean(composer.thread)).toBe(false);
    expectRecord(marc).not.toBeIn(thread.members);
    expect(thread.members).toBeEmpty();
    expectRecord(hello).not.toBeIn(thread.messages);
    expectRecord(thread).not.toBeIn(hello.threads);
    expect(thread.messages).toBeEmpty();
});

test("Assign & Delete on _inherits fields", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        channel = fields.One("Channel", { inverse: "thread" });
        pluriChannels = fields.Many("PluriChannel", { inverse: "thread" });
    }).register(localRegistry);
    (class Channel extends Record {
        static id = "id";
        static _inherits = { Thread: "thread" };
        id;
        thread = fields.One("Thread", { inverse: "channel" });
    }).register(localRegistry);
    (class PluriChannel extends Record {
        static id = "id";
        static _inherits = { Thread: "thread" };
        id;
        thread = fields.One("Thread", { inverse: "pluriChannels" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const channel = store.Channel.insert({ id: 1, thread: thread });
    const [pluriChannel1, pluriChannel2] = store.PluriChannel.insert([
        { id: 1, thread },
        { id: 2, thread },
    ]);
    expectRecord(channel).toEqual(thread.channel);
    expectRecord(pluriChannel1).toBeIn(thread.pluriChannels);
    expectRecord(pluriChannel2).toBeIn(thread.pluriChannels);
    thread.delete();
    expect(thread.pluriChannels).toBeEmpty();
    expect(pluriChannel1.exists()).toBe(false);
    expect(pluriChannel2.exists()).toBe(false);
    expect(Boolean(thread.channel)).toBe(false);
    expect(channel.exists()).toBe(false);
});

test("onRelationChange on relational with inverse", async () => {
    let logs = [];
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Member", { inverse: "thread" });
        setup() {
            this.onRelationChange(
                () => this.members,
                ({ added, removed }) => {
                    added.forEach((member) => logs.push(`Thread.onAdd(${member.name})`));
                    removed.forEach((member) => logs.push(`Thread.onDelete(${member.name})`));
                }
            );
        }
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        thread = fields.One("Thread");
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

test("insert on html field", async () => {
    (class Message extends Record {
        static id = "body";
        body = fields.Html("");
    }).register(localRegistry);
    const store = await start();
    const message1 = store.Message.insert({ body: ["markup", "<p>hello 1</p>"] });
    expect(message1.body?.toString()).toBe("<p>hello 1</p>");
    expect(message1.body).toBeInstanceOf(Markup);
    message1.body = "<p>hello 1b</p>";
    expect(message1.body?.toString()).toBe("&lt;p&gt;hello 1b&lt;/p&gt;");
    const message2 = store.Message.insert("<p>hello 2</p>");
    expect(message2.body?.toString()).toBe("&lt;p&gt;hello 2&lt;/p&gt;");
    expect(message2.body).toBeInstanceOf(Markup);
    message2.body = ["markup", "<p>hello 2b</p>"];
    expect(message2.body?.toString()).toBe("<p>hello 2b</p>");
    message2.body = ["markup", false];
    expect(message2.body).toBe("");
    expect(message2.body).not.toBeInstanceOf(Markup);
    const message3 = store.Message.insert({ body: markup`<p>hello 3</p>` });
    expect(message3.body?.toString()).toBe("<p>hello 3</p>");
    expect(message3.body).toBeInstanceOf(Markup);
    message3.body = false;
    expect(message3.body).toBe("");
    expect(message3.body).not.toBeInstanceOf(Markup);
});

test("Unshift preserves order", async () => {
    (class Message extends Record {
        static id = "id";
        id;
    }).register(localRegistry);
    (class Thread extends Record {
        static id = "name";
        name;
        messages = fields.Many("Message");
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

test("Can insert with relation as id, using relation as data object", async () => {
    (class User extends Record {
        static id = "name";
        name;
        settings = fields.One("Settings");
    }).register(localRegistry);
    (class Settings extends Record {
        static id = "user";
        pushNotif;
        user = fields.One("User", { inverse: "settings" });
    }).register(localRegistry);
    const store = await start();
    store.Settings.insert([
        { pushNotif: true, user: { name: "John" } },
        { pushNotif: false, user: { name: "Paul" } },
    ]);
    expect(store.User.get("John").settings.pushNotif).toBe(true);
    expect(store.User.get("Paul").settings.pushNotif).toBe(false);
});

test("Set on attr should invoke onChange", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        body;
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert(1);
    message.onChange(
        () => [message.body],
        () => expect.step("BODY_CHANGED"),
        { immediate: true, initialRun: false }
    );
    expect.verifySteps([]);
    message.update({ body: "test1" });
    expect.verifySteps(["BODY_CHANGED"]);
    message.body = "test2";
    expect.verifySteps(["BODY_CHANGED"]);
});

test("onChange with spread Many deps fires on relation content changes", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Persona");
    }).register(localRegistry);
    (class Persona extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    thread.onChange(
        () => [...thread.members],
        (...members) => expect.step(`MEMBERS:${members.map((m) => m.name).join(",")}`),
        { immediate: true, initialRun: false }
    );
    thread.members.add("John");
    expect.verifySteps(["MEMBERS:John"]);
    thread.members.add("Marc");
    expect.verifySteps(["MEMBERS:John,Marc"]);
    thread.members.delete("John");
    expect.verifySteps(["MEMBERS:Marc"]);
});

test("record list sort should be manually observable", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        messages = fields.Many("Message", { inverse: "thread" });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        body;
        author;
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert(1);
    const messages = store.Message.insert([
        { id: 1, body: "a", thread },
        { id: 2, body: "b", thread },
    ]);
    function sortMessages() {
        thread.messages.sort((m1, m2) => {
            if (m1.body < m2.body) {
                return -1;
            }
            if (m1.body > m2.body) {
                return 1;
            }
            return m1.id - m2.id;
        });
        expect.step(`sortMessages`);
    }
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    const disposeFn = immediateEffect(() => {
        sortMessages();
    });
    after(() => disposeFn());
    expect(`${thread.messages.map((m) => m.id)}`).toBe("1,2");
    expect.verifySteps(["sortMessages"]);
    messages[0].body = "c";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    expect.verifySteps(["sortMessages"]);
    messages[0].body = "d";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    expect.verifySteps(["sortMessages"]);
    messages[0].author = "Jane";
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,1");
    expect.verifySteps([]);
    store.Message.insert({ id: 3, body: "c", thread });
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,3,1");
    expect.verifySteps(["sortMessages", "sortMessages"]);
    messages[0].delete();
    expect(`${thread.messages.map((m) => m.id)}`).toBe("2,3");
    expect.verifySteps(["sortMessages"]);
});

test("store updates can be observed", async () => {
    localRegistry.remove("Store");
    (class extends Store {
        static _name = "Store";
        abc;
    }).register(localRegistry);
    const store = await start();
    function onUpdate() {
        expect.step(`abc:${store.abc}`);
    }
    const disposeFn = immediateEffect(() => {
        onUpdate();
    });
    after(() => disposeFn());
    expect.verifySteps(["abc:undefined"]);
    store.abc = 1;
    expect.verifySteps(["abc:1"]); // observable from makeStore"
    store.store.abc = 2;
    expect.verifySteps(["abc:2"]); // observable from record.store
    store.Model.store.abc = 3;
    expect.verifySteps(["abc:3"]);
});

test("onRelationChange on one without inverse", async () => {
    (class Thread extends Record {
        static id = "name";
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        thread = fields.One("Thread");
        setup() {
            this.onRelationChange(
                () => this.thread,
                ({ added, removed }) => {
                    added.forEach((thread) => expect.step(`thread.onAdd(${thread.name})`));
                    removed.forEach((thread) => expect.step(`thread.onDelete(${thread.name})`));
                }
            );
        }
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    const john = store.Member.insert("John");
    await expect.waitForSteps([]);
    john.thread = general;
    await expect.waitForSteps(["thread.onAdd(General)"]);
    john.thread = general;
    await expect.waitForSteps([]);
    john.thread = undefined;
    await expect.waitForSteps(["thread.onDelete(General)"]);
});

test("onRelationChange on many without inverse", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Member");
        setup() {
            this.onRelationChange(
                () => this.members,
                ({ added, removed }) => {
                    added.forEach((member) => expect.step(`members.onAdd(${member.name})`));
                    removed.forEach((member) => expect.step(`members.onDelete(${member.name})`));
                }
            );
        }
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    const jane = store.Member.insert("Jane");
    const john = store.Member.insert("John");
    await expect.waitForSteps([]);
    general.members = jane;
    await expect.waitForSteps(["members.onAdd(Jane)"]);
    general.members = jane;
    await expect.waitForSteps([]);
    general.members = [["ADD", john]];
    await expect.waitForSteps(["members.onAdd(John)"]);
    general.members = undefined;
    await expect.waitForSteps(["members.onDelete(Jane)", "members.onDelete(John)"]);
});

test("onRelationChange sees the changes made by its own callback", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Member");
        setup() {
            this.onRelationChange(
                () => this.members,
                ({ added }) => {
                    added.forEach((member) => expect.step(`added(${member.name})`));
                    while (this.members.length > 1) {
                        const member = this.members.pop();
                        expect.step(`popped(${member.name})`);
                    }
                }
            );
        }
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const [john, marc] = store.Member.insert(["John", "Marc"]);
    thread.members.add(john);
    expect.verifySteps(["added(John)"]);
    thread.members.unshift(marc);
    expect.verifySteps(["added(Marc)", "popped(John)"]);
    thread.members.add(john);
    expect.verifySteps(["added(John)", "popped(John)"]);
});

test("record list assign should update inverse fields", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Member", { inverse: "thread" });
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        thread = fields.One("Thread", { inverse: "members" });
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    const jane = store.Member.insert("Jane");
    general.members = jane; // direct assignation of value goes through assign()
    expectRecord(jane.thread).toEqual(general);
    general.members = []; // writing empty array specifically goes through assign()
    expect(Boolean(jane.thread)).toBe(false);
    jane.thread = general;
    expectRecord(jane).toBeIn(general.members);
    jane.thread = [];
    expectRecord(jane).not.toBeIn(general.members);
});

test("datetime type record", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        setup() {
            super.setup();
            this.onChange(
                () => [this.date],
                () => expect.step("DATE_UPDATED"),
                { initialRun: false }
            );
        }
        date = fields.Attr(undefined, { type: "datetime" });
    }).register(localRegistry);
    const store = await start();
    await expect.waitForSteps([]);
    const general = store.Thread.insert({ name: "General", date: "2024-02-20 14:42:00" });
    await expect.waitForSteps(["DATE_UPDATED"]);
    expect(general.date).toBeInstanceOf(luxon.DateTime);
    expect(general.date.day).toBe(20);
    store.Thread.insert({ name: "General", date: "2024-02-21 14:42:00" });
    await expect.waitForSteps(["DATE_UPDATED"]);
    expect(general.date.day).toBe(21);
    store.Thread.insert({ name: "General", date: "2024-02-21 14:42:00" });
    await expect.waitForSteps([]);
    store.Thread.insert({ name: "General", date: undefined });
    await expect.waitForSteps(["DATE_UPDATED"]);
    expect(general.date).toBe(undefined);
    const now = luxon.DateTime.now();
    const thread = store.Thread.insert({ name: "General", date: now });
    await expect.waitForSteps(["DATE_UPDATED"]);
    expect(thread.date).toBeInstanceOf(luxon.DateTime);
    expect(thread.date.equals(now)).toBe(true);
    store.Thread.insert({ name: "General", date: false });
    await expect.waitForSteps(["DATE_UPDATED"]);
    expect(general.date).toBe(false);
    store.Thread.insert({ name: "General", date: "2024-02-22 14:42:00" });
    await expect.waitForSteps(["DATE_UPDATED"]);
    expect(general.date.day).toBe(22);
});

test("attr that are default [] should be isolated per record", async () => {
    // If the default value is stored and reused for all records,
    // this could lead to mistakenly sharing the default value among records
    (class Person extends Record {
        static id = "id";
        id;
        names = fields.Attr([]);
    }).register(localRegistry);
    const store = await start();
    const p1 = store.Person.insert({ id: 1 });
    const p2 = store.Person.insert({ id: 2 });
    expect(p1.names).toEqual([]);
    expect(p2.names).toEqual([]);
    p1.names.push("John");
    expect(p1.names).toEqual(["John"]);
    expect(p2.names).toEqual([]);
});

test("in-place mutation of an array attr is reactive", async () => {
    (class Person extends Record {
        static id = "id";
        id;
        names = fields.Attr([], { asProxy: true });
    }).register(localRegistry);
    const store = await start();
    const person = store.Person.insert({ id: 1 });
    const disposeFn = immediateEffect(() => {
        expect.step(`names:${person.names.length}`);
    });
    after(() => disposeFn());
    expect.verifySteps(["names:0"]);
    person.names.push("John");
    expect.verifySteps(["names:1"]);
    person.names.push("Jane");
    expect.verifySteps(["names:2"]);
    person.names = [];
    expect.verifySteps(["names:0"]);
});

test("record.toData() is JSON stringified and can be reinserted as record", async () => {
    // If the default value is stored and reused for all records,
    // this could lead to mistakenly sharing the default value among records
    (class Person extends Record {
        static id = "id";
        id;
        names = fields.Attr([]);
        due_datetime = fields.Attr(undefined, { type: "datetime" });
        messages = fields.Many("Message");
        team = fields.One("Team");
        signature = fields.Html("");
        get isDiscuss() {
            return this.team === "Discuss";
        }
    }).register(localRegistry);
    (class Message extends Record {
        static id = "body";
        body = fields.Attr("");
    }).register(localRegistry);
    (class Team extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const p = store.Person.insert({
        id: 1,
        due_datetime: "2024-08-28 10:19:44",
        names: ["John", "Marc"],
        messages: [{ body: "1" }, { body: "2" }],
        team: "Discuss",
        signature: ["markup", "<p>-- John</p>"],
    });
    expect(p.names).toEqual(["John", "Marc"]);
    expect(p.messages.map((msg) => msg.body)).toEqual(["1", "2"]);
    expect(p.team.name).toBe("Discuss");
    expect(p.signature.toString()).toBe("<p>-- John</p>");
    expect(p.signature).toBeInstanceOf(Markup);
    expect(store.Person.records.get(p.localId)).toBe(p);
    expect(serializeDateTime(p.due_datetime)).toBe("2024-08-28 10:19:44");
    // export data, delete, then insert back
    const data = p.toData();
    // ensure no computed field
    expect(data).toEqual({
        Person: [
            {
                id: 1,
                due_datetime: "2024-08-28 10:19:44",
                names: ["John", "Marc"],
                messages: [{ body: "1" }, { body: "2" }],
                team: { name: "Discuss" },
                signature: ["markup", "<p>-- John</p>"],
            },
        ],
    });
    const serializedData = JSON.parse(JSON.stringify(data));
    p.delete();
    store.Message.get("1").delete();
    store.Message.get("2").delete();
    store.Team.get("Discuss").delete();
    expect(store.Person.records.get(p.localId)).toBe(undefined);
    store.insert(serializedData);
    const p2 = store.Person.get(1);
    // Same assertions as before
    expect(p2.names).toEqual(["John", "Marc"]);
    expect(p2.messages.map((msg) => msg.body)).toEqual(["1", "2"]);
    expect(p2.team.name).toBe("Discuss");
    expect(store.Person.records.get(p2.localId)).toBe(p2);
    expect(serializeDateTime(p2.due_datetime)).toBe("2024-08-28 10:19:44");
    expect(p2.signature.toString()).toBe("<p>-- John</p>");
    expect(p.signature).toBeInstanceOf(Markup);
});

test("record.toData() returns flat data", async () => {
    (class Person extends Record {
        static id = "id";
        id;
        names = fields.Attr([]);
        due_datetime = fields.Attr(undefined, { type: "datetime" });
        messages = fields.Many("Message");
        team = fields.One("Team");
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        body = fields.Attr("");
    }).register(localRegistry);
    (class Team extends Record {
        static id = "id";
        id;
        name;
        leader = fields.One("Person");
    }).register(localRegistry);
    const store = await start();
    store.Person.insert([
        {
            id: 1,
            due_datetime: "2024-08-28 10:19:44",
            names: ["Seb", "Theys"],
            messages: [
                { id: 1, body: "1" },
                { id: 2, body: "2" },
            ],
            team: { id: 1, name: "Discuss", leader: { id: 2 } },
        },
        {
            id: 2,
            due_datetime: "2025-01-23 12:12:12",
            names: ["Louis", "Wicket"],
            messages: [
                { id: 1, body: "1" },
                { id: 3, body: "3" },
            ],
            team: { id: 2, name: "VoIP", leader: { id: 1 } },
        },
    ]);
    const p = store.Person.get(1);
    expect(p.toData()).toEqual({
        Person: [
            {
                id: 1,
                due_datetime: "2024-08-28 10:19:44",
                names: ["Seb", "Theys"],
                messages: [{ id: 1 }, { id: 2 }],
                team: { id: 1 },
            },
        ],
    });
    expect(p.toData(["messages", "team"])).toEqual({
        Person: [
            {
                id: 1,
                due_datetime: "2024-08-28 10:19:44",
                names: ["Seb", "Theys"],
                messages: [{ id: 1 }, { id: 2 }],
                team: { id: 1 },
            },
        ],
        Message: [
            { id: 1, body: "1" },
            { id: 2, body: "2" },
        ],
        Team: [{ id: 1, name: "Discuss", leader: { id: 2 } }],
    });
    expect(p.toData(["team.leader"])).toEqual({
        Person: [
            {
                id: 2,
                due_datetime: "2025-01-23 12:12:12",
                names: ["Louis", "Wicket"],
                messages: [{ id: 1 }, { id: 3 }],
                team: { id: 2 },
            },
            {
                id: 1,
                due_datetime: "2024-08-28 10:19:44",
                names: ["Seb", "Theys"],
                messages: [{ id: 1 }, { id: 2 }],
                team: { id: 1 },
            },
        ],
        Team: [{ id: 1, name: "Discuss", leader: { id: 2 } }],
    });
    expect(p.toData({ depth: true })).toEqual({
        Person: [
            {
                id: 2,
                due_datetime: "2025-01-23 12:12:12",
                names: ["Louis", "Wicket"],
                messages: [{ id: 1 }, { id: 3 }],
                team: { id: 2 },
            },
            {
                id: 1,
                due_datetime: "2024-08-28 10:19:44",
                names: ["Seb", "Theys"],
                messages: [{ id: 1 }, { id: 2 }],
                team: { id: 1 },
            },
        ],
        Message: [
            { id: 1, body: "1" },
            { id: 2, body: "2" },
            { id: 3, body: "3" },
        ],
        Team: [
            { id: 2, name: "VoIP", leader: { id: 1 } },
            { id: 1, name: "Discuss", leader: { id: 2 } },
        ],
    });
});

test("Methods are bound to records", async () => {
    // Allows to simply `t-on-click="record.method"`
    (class Persona extends Record {
        static id = "name";
        name;
        saysName() {
            return this.name;
        }
    }).register(localRegistry);
    const store = await start();
    const john = store.Persona.insert("John");
    expect(john.saysName()).toBe("John");
    const saysName = john.saysName;
    expect(saysName()).toBe("John");
});

test("Record lists methods are bound to the record list", async () => {
    // Allows to simply `onSelected="recordList.add"`
    (class Message extends Record {
        static id = "content";
        content;
    }).register(localRegistry);
    (class Thread extends Record {
        static id = "name";
        name;
        messages = fields.Many("Message");
    }).register(localRegistry);
    const store = await start();
    const general = store.Thread.insert("General");
    expect(general.messages.length).toBe(0);
    const addMessage = general.messages.add;
    addMessage({ content: "1" });
    expect(general.messages.length).toBe(1);
    expect(general.messages.map((msg) => msg.content)).toEqual(["1"]);
});

test("setup() has precedence over instance class field definition", async () => {
    class Test extends Record {}
    Test.register(localRegistry);
    (class Test2 extends Test {
        x = false;
        setup() {
            super.setup();
            this.x = true;
        }
    }).register(localRegistry);
    const store = await start();
    const test = store.Test2.insert();
    expect(test.x).toBe(true);
});

test("insert with id relation keeps existing field values", async () => {
    class User extends Record {
        static id = "id";
        id;
    }
    User.register(localRegistry);
    class Thread extends Record {
        static id = "id";
        id;
    }
    Thread.register(localRegistry);
    class ChannelMember extends Record {
        static id = AND("channel", "user");
        is_internal = fields.Attr(false);
        channel = fields.One("Thread");
        user = fields.One("User");
    }
    ChannelMember.register(localRegistry);
    const store = await start();
    const member1 = store.ChannelMember.insert({
        is_internal: true,
        user: { id: 1 },
        channel: { id: 2 },
    });
    const user1 = member1.user;
    const channel1 = member1.channel;
    expect(member1.is_internal).toBe(true);
    const member2 = store.ChannelMember.insert({
        user: { id: 1 },
        channel: { id: 2 },
    });
    expect(member2.eq(member1)).toBe(true);
    expect(member2.user.eq(user1)).toBe(true);
    expect(member2.channel.eq(channel1)).toBe(true);
    expect(member2.is_internal).toBe(true);
});

test("Inserting single-id data on non-single id Model throws human-readable error", async () => {
    (class Persona extends Record {
        static id = AND("partner_id", "guest_id");
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        id;
        author = fields.One("Persona");
    }).register(localRegistry);
    const store = await start();
    store._.warnErrors = false;
    const paul = store.Persona.insert({ partner_id: 1 });
    store.Persona.insert({ guest_id: 2 });
    expect(store.Persona.get({ partner_id: 1 }).exists()).toBe(true);
    expect(store.Persona.get({ guest_id: 2 }).exists()).toBe(true);
    expect(store.Persona.get(1)).toBe(undefined);
    expect(store.Persona.get(2)).toBe(undefined);
    expect(() => store.Persona.insert(3)).toThrow(
        `Cannot insert "3" on model "Persona": this model doesn't support single-id data!`
    );
    const msg = store.Message.insert(100);
    expect(() => (msg.author = 1)).toThrow(
        `Cannot insert "1" on relational field "Message/author": target model "Persona" doesn't support single-id data!`
    );
    msg.author = { partner_id: 1 };
    expectRecord(msg.author).toEqual(paul);
});

test("Can assign new record on Many field with One inverse", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        files = fields.Many("File", { inverse: "thread" });
    }).register(localRegistry);
    (class File extends Record {
        static id = "name";
        thread = fields.One("Thread", { inverse: "files" });
        name;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    const file1 = store.File.insert("file1.txt");
    const file2 = store.File.insert("file2.txt");
    const file3 = store.File.insert("file3.txt");
    const file4 = store.File.insert("file4.txt");
    const file2Replacement = store.File.insert("file2repl.txt");
    thread.files.push(file1, file2, file3, file4);
    expect(thread.files.length).toBe(4);
    expectRecord(thread.files[1]).toEqual(file2);
    expectRecord(file2.thread).toEqual(thread);
    expect(file2Replacement.thread).toBe(undefined);
    thread.files[1] = file2Replacement;
    expect(thread.files.length).toBe(4);
    expectRecord(thread.files[1]).toEqual(file2Replacement);
    expectRecord(file2Replacement.thread).toEqual(thread);
    expect(file2.thread).toBe(undefined);
});

test("Deleted records are not returned by 'Model.records' nor 'Model.get()'", async () => {
    /**
     * Record has a 2-step record deletion:
     * - "soft" deletion, where the record is flagged for deletion but object is not removed from the store system structurally
     * - "hard" deletion, where the object is fully removed from store system structurally
     * with object reference, even when the record will be hard-deleted as a consequence.
     * `Model.records` and `Model.get()` are intended for business-code uses, therefore they should make sure to not return
     * records that are soft-deleted, as this could lead to critical section where business code is using a deleted record.
     */
    function assertExists(store) {
        const msg = store.Message.get("msg-1");
        if (msg) {
            expect(msg.exists()).toBe(true);
        }
        for (const msg of store.Message.records.values()) {
            expect(msg.exists()).toBe(true);
        }
    }
    let deleting = false;
    (class Thread extends Record {
        static id = "name";
        name;
        messages = fields.Many("Message", { inverse: "thread" });
        get hasMessages() {
            return this.messages.length > 0;
        }
    }).register(localRegistry);
    (class Message extends Record {
        static id = "content";
        content;
        thread = fields.One("Thread");
    }).register(localRegistry);
    (class DiscussApp extends Record {
        static id = "id";
        id;
        thread = fields.One("Thread");
        allMessagesInStore = fields.Many("Message");
        setup() {
            this.onChange(
                () => [...this.store.Message.records.values()],
                function (...messages) {
                    if (deleting) {
                        expect.step("allMessagesInStore:onchange");
                    }
                    assertExists(this.store);
                    this.allMessagesInStore = messages;
                },
                { immediate: true }
            );
        }
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert({ name: "General" });
    store.DiscussApp.insert({ thread });
    const message = store.Message.insert({ content: "msg-1", thread });
    expectRecord(thread.messages[0]).toEqual(message);
    expectRecord(store.Message.get("msg-1")).toEqual(message);
    expectRecord(store.Message.records.get(message.localId)).toEqual(message);
    deleting = true;
    message.delete();
    deleting = false;
    expect.verifySteps(["allMessagesInStore:onchange"]);
    assertExists(store);
    expect(thread.messages.length).toEqual(0);
});

test("Can delete record with chained onRelationChange: () => record.delete()", async () => {
    (class Channel extends Record {
        static id = "name";
        name;
        thread = fields.One("Thread", { inverse: "channel" });
        setup() {
            this.onRelationChange(
                () => this.thread,
                ({ removed }) => removed.forEach((thread) => thread.delete())
            );
        }
    }).register(localRegistry);
    (class Thread extends Record {
        static id;
        channel = fields.One("Channel", { inverse: "thread" });
        correspondent = fields.One("User");
        members = fields.Many("User", { inverse: "threads" });
        setup() {
            this.assignComputed("correspondent", function computeCorrespondent() {
                return this.members[0];
            });
            this.onRelationChange(
                () => this.members,
                ({ removed }) => removed.forEach((user) => user.delete())
            );
        }
    }).register(localRegistry);
    (class User extends Record {
        static id = "name";
        name;
        threads = fields.Many("Thread");
    }).register(localRegistry);
    const store = await start();
    const john = store.User.insert("john");
    const thread = store.Thread.insert({ channel: "general", members: [john] });
    expectRecord(thread.correspondent).toEqual(john); // intentional observing correspondent field for compute on thread deletion
    thread.delete();
    expect(thread.exists()).toBe(false);
});

test("getters patched after the store is made are honored", async () => {
    const Thread = class Thread extends Record {
        static id = "name";
        name;
        get label() {
            return `Thread: ${this.name}`;
        }
    };
    Thread.register(localRegistry);
    const store = await start();
    patchWithCleanup(Thread.prototype, {
        get label() {
            return `${super.label} (patched)`;
        },
    });
    expect(store.Thread.insert("general").label).toBe("Thread: general (patched)");
});

test("record.delete() empties its own relations", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Member");
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const john = store.Member.insert({ name: "john" });
    const thread = store.Thread.insert({ name: "general", members: [john] });
    const disposeFn = immediateEffect(() => expect.step(`members:${thread.members.length}`));
    after(() => disposeFn());
    expect.verifySteps(["members:1"]);
    thread.delete();
    expect(john.exists()).toBe(true);
    expect.verifySteps(["members:0"]);
});

test("record deleted from the deletion of another leaves its relations", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        members = fields.Many("Member", { inverse: "thread" });
        onlineMembers = fields.Many("Member");
        setup() {
            this.assignComputed("onlineMembers", function computeOnlineMembers() {
                return this.members.filter((member) => member.online);
            });
        }
    }).register(localRegistry);
    (class Member extends Record {
        static id = "name";
        name;
        online = false;
        thread = fields.One("Thread", { inverse: "members" });
        setup() {
            this.onRelationChange(
                () => this.thread,
                ({ removed }) => {
                    if (removed.length) {
                        this.delete();
                    }
                }
            );
        }
    }).register(localRegistry);
    const store = await start();
    const john = store.Member.insert({ name: "john", online: true });
    const thread = store.Thread.insert({ name: "general", members: [john] });
    expect(thread.onlineMembers.length).toBe(1);
    expectRecord(john).toBeIn(thread.onlineMembers);
    thread.delete();
    expect(john.exists()).toBe(false);
    expect(thread.onlineMembers.length).toBe(0);
});

test("fields, getters and functions are inherited", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        channel = fields.One("Channel", { inverse: "thread" });
        setup() {
            this.assignComputed("channel", function computeChannel() {
                return this.id;
            });
        }
        name;
        get displayName() {
            return `Thread: ${this.name}`;
        }
        getName() {
            return `Thread: ${this.name}`;
        }
    }).register(localRegistry);
    (class Channel extends Record {
        static id = "id";
        static _inherits = { Thread: "thread" };
        id;
        thread = fields.One("Thread", { inverse: "channel" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert({ id: 1, name: "General" });
    expect(thread.name).toBe("General");
    expect(thread.channel.name).toBe("General");
    expect(thread.displayName).toBe("Thread: General");
    expect(thread.channel.displayName).toBe("Thread: General");
    expect(thread.getName()).toBe("Thread: General");
    expect(thread.channel.getName()).toBe("Thread: General");
});

test("shadowed fields, getters and functions are not inherited", async () => {
    (class Thread extends Record {
        static id = "id";
        id;
        channel = fields.One("Channel", { inverse: "thread" });
        setup() {
            this.assignComputed("channel", function computeChannel() {
                return this.id;
            });
        }
        name;
        get displayName() {
            return `Thread: ${this.name}`;
        }
        getName() {
            return `Thread: ${this.name}`;
        }
    }).register(localRegistry);
    (class Channel extends Record {
        static id = "id";
        static _inherits = { Thread: "thread" };
        id;
        thread = fields.One("Thread", { inverse: "channel" });
        name;
        get displayName() {
            return `Channel: ${this.name}`;
        }
        getName() {
            return `Channel: ${this.name}`;
        }
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert({ id: 1, name: "General" });
    expect(thread.name).toBe("General");
    expect(thread.channel.name).toBeEmpty();
    expect(thread.displayName).toBe("Thread: General");
    expect(thread.channel.displayName).toBe("Channel: undefined");
    expect(thread.getName()).toBe("Thread: General");
    expect(thread.channel.getName()).toBe("Channel: undefined");
});

test("accessing fields through empty _inherits parent returns empty values", async () => {
    (class Partner extends Record {
        static id = "id";
        id;
        name;
        users = fields.Many("User", { inverse: "partner" });
        partners = fields.Many("Partner");
    }).register(localRegistry);
    (class User extends Record {
        static id = "id";
        static _inherits = { Partner: "partner" };
        id;
        partner = fields.One("Partner", { inverse: "users" });
    }).register(localRegistry);
    const store = await start();
    const user = store.User.insert({ id: 1 });
    expect(user.partner).toBe(undefined);
    expect(user.name).toBe(undefined);
    // a parent with no record yet has no field registered, so its name is not
    // resolved and reads plain undefined
    expect(user.partners).toBe(undefined);
    user.partner = { id: 2, name: "John" };
    expect(user.name).toBe("John");
    expect(user.partners).toHaveLength(0);
});

test("A field declared with localStorage() is saved in local storage", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        setup() {
            super.setup();
            this.body = this.localStorage("");
        }
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert(1);
    const bodyLocalId = makeRecordFieldLocalId(message.localId, "body");
    expect(localStorage.getItem(bodyLocalId)).toBe(null);
    message.body = "test";
    expect(localStorage.getItem(bodyLocalId)).toBe(toRawValue("test"));
    message.body = "test2";
    expect(localStorage.getItem(bodyLocalId)).toBe(toRawValue("test2"));
});

test("A field declared with localStorage() is restored from local storage", async () => {
    class Message extends Record {
        static id = "id";
        id;
        setup() {
            super.setup();
            this.body = this.localStorage("");
        }
    }
    Message.register(localRegistry);
    const bodyLocalId = makeRecordFieldLocalId(Message.localId(1), "body");
    localStorage.setItem(bodyLocalId, toRawValue("test"));
    const store = await start();
    const message = store.Message.insert(1);
    expect(message.body).toBe("test");
});

test("localStorage entry equal to the field default is dropped on restore", async () => {
    class Message extends Record {
        static id = "id";
        id;
        setup() {
            super.setup();
            this.body = this.localStorage("hello");
        }
    }
    Message.register(localRegistry);
    const bodyLocalId = makeRecordFieldLocalId(Message.localId(1), "body");
    localStorage.setItem(bodyLocalId, toRawValue("hello"));
    const store = await start();
    const message = store.Message.insert(1);
    expect(message.body).toBe("hello");
    expect(localStorage.getItem(bodyLocalId)).toBe(null);
    message.body = "world";
    expect(localStorage.getItem(bodyLocalId)).toBe(toRawValue("world"));
});

test("Fields updated from the local storage do not trigger another storage event", async () => {
    class Message extends Record {
        static id = "id";
        id;
        setup() {
            super.setup();
            this.body = this.localStorage("");
        }
    }
    Message.register(localRegistry);
    const bodyLocalId = makeRecordFieldLocalId(Message.localId(1), "body");
    patchWithCleanup(browser.localStorage, {
        setItem(key, value) {
            if (key === bodyLocalId) {
                expect.step(`setItem ${JSON.parse(value).value}`);
            }
            return super.setItem(key, value);
        },
    });
    localStorage.setItem(bodyLocalId, toRawValue("1"));
    await expect.waitForSteps(["setItem 1"]);
    const store = await start();
    const message = store.Message.insert(1);
    expect(message.body).toBe("1");
    message.body = "2";
    expect(message.body).toBe("2");
    await expect.waitForSteps(["setItem 2"]);
    browser.dispatchEvent(
        new StorageEvent("storage", { key: bodyLocalId, newValue: toRawValue("3") })
    );
    await tick();
    expect(message.body).toBe("3");
    await expect.waitForSteps([]);
});

test("Record exists is reactive", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("General");
    const disposeFn = immediateEffect(() => {
        if (thread.exists()) {
            expect.step("thread exists");
        } else {
            expect.step("thread does not exist");
        }
    });
    after(() => disposeFn());
    expect.verifySteps(["thread exists"]);
    thread.delete();
    expect.verifySteps(["thread does not exist"]);
});

test("Normalize many commands", () => {
    // Falsy values or empty array are interpreted as clear.
    for (const clearValues of [null, undefined, false, []]) {
        expect(normalizeManyCommands(clearValues)).toEqual([["REPLACE", []]]);
    }
    // Raw values are interpreted as "REPLACE".
    expect(normalizeManyCommands({ id: 1, name: "Test" })).toEqual([
        ["REPLACE", [{ id: 1, name: "Test" }]],
    ]);
    expect(normalizeManyCommands([1, 2, 3])).toEqual([["REPLACE", [1, 2, 3]]]);
    // Commands with non array value should normalize to array.
    expect(normalizeManyCommands(["ADD", { id: 10 }])).toEqual([["ADD", [{ id: 10 }]]]);
    const cmdList = [
        ["ADD", { id: 1 }],
        ["DELETE", { id: 2 }],
    ];
    expect(normalizeManyCommands(cmdList)).toEqual([
        ["ADD", [{ id: 1 }]],
        ["DELETE", [{ id: 2 }]],
    ]);
    // Single command should normalize to command list including the command.
    expect(normalizeManyCommands(["DELETE", [10, 20]])).toEqual([["DELETE", [10, 20]]]);
    // Mixed of raw values and commands should throw error.
    const mixed = [1, ["ADD", 2]];
    expect(() => normalizeManyCommands(mixed)).toThrow(
        "Many commands cannot mix raw values and commands"
    );
});

test("observers of a record created by a component outlive that component", async () => {
    (class Persona extends Record {
        static id = "name";
        name;
        counter = 0;
    }).register(localRegistry);
    const store = await start();
    let persona;
    class Creator extends Component {
        static props = {};
        static template = xml`<t/>`;
        setup() {
            persona = store.Persona.insert("John");
            persona.onChange(
                () => [persona.counter],
                () => expect.step(`counter:${persona.counter}`),
                { immediate: true, initialRun: false }
            );
        }
    }
    class Parent extends Component {
        static components = { Creator };
        static props = {};
        static template = xml`<Creator t-if="this.state.hasCreator"/>`;
        setup() {
            this.state = proxy({ hasCreator: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    persona.counter = 1;
    expect.verifySteps(["counter:1"]);
    parent.state.hasCreator = false;
    await animationFrame();
    persona.counter = 2;
    expect.verifySteps(["counter:2"]);
});

test("computed field first read by a component outlives that component", async () => {
    (class Channel extends Record {
        static id = "id";
        id;
        count = 0;
        multiplicity = this.computed(() => (this.count > 3 ? "many" : "few"));
    }).register(localRegistry);
    const store = await start();
    const channel = store.Channel.insert(1);
    class Reader extends Component {
        static props = {};
        static template = xml`<t/>`;
        setup() {
            expect.step(`read:${channel.multiplicity}`);
        }
    }
    class Parent extends Component {
        static components = { Reader };
        static props = {};
        static template = xml`<Reader t-if="this.state.hasReader"/>`;
        setup() {
            this.state = proxy({ hasReader: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    expect.verifySteps(["read:few"]);
    const disposeFn = immediateEffect(() => expect.step(`multiplicity:${channel.multiplicity}`));
    after(() => disposeFn());
    expect.verifySteps(["multiplicity:few"]);
    parent.state.hasReader = false;
    await animationFrame();
    channel.count = 5;
    expect.verifySteps(["multiplicity:many"]);
});

test("a record is its proxy in a field declaration and in setup", async () => {
    (class Message extends Record {
        static id = "id";
        id;
        author = fields.One("Partner");
        readAuthorFromDeclaration = () => this.author;
        readAuthorFromSetup;
        setup() {
            super.setup(...arguments);
            this.readAuthorFromSetup = () => this.author;
        }
    }).register(localRegistry);
    (class Partner extends Record {
        static id = "name";
        name;
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert({ id: 1, author: "John" });
    expectRecord(message.readAuthorFromDeclaration()).toEqual(message.author);
    expectRecord(message.readAuthorFromSetup()).toEqual(message.author);
});

test("a computed is not a field", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        label = this.computed(() => "a thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    expect(thread.label).toBe("a thread");
    expect(Object.keys(thread.toData())).not.toInclude("label");
});

test("a declared computed runs again only when what it read changes", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        counter = 0;
        label = this.computed(() => {
            expect.step(`label ${this.counter}`);
            return `label ${this.counter}`;
        });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    expect(thread.label).toBe("label 0");
    expect(thread.label).toBe("label 0");
    expect.verifySteps(["label 0"]);
    thread.counter = 1;
    expect(thread.label).toBe("label 1");
    expect.verifySteps(["label 1"]);
});

test("a getter runs on every read", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        get label() {
            expect.step("label");
            return "label";
        }
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    expect(thread.label).toBe("label");
    expect(thread.label).toBe("label");
    expect.verifySteps(["label", "label"]);
});

test("a patch cannot redeclare a computed", async () => {
    patchWithCleanup(console, { warn: () => {} });
    const Thread = class Thread extends Record {
        static id = "name";
        name;
        label = this.computed(() => "base");
    };
    Thread.register(localRegistry);
    patchWithCleanup(Thread.prototype, {
        setup() {
            super.setup();
            this.label = this.computed(() => "patched");
        },
    });
    const store = await start();
    // a model's fields are declared by its first record, so the redeclaration
    // is caught on the first insert, not at store creation
    expect(() => store.Thread.insert("General")).toThrow(/cannot be redeclared/);
});

test("a computed does not recompute once its record is deleted", async () => {
    (class Thread extends Record {
        static id = "name";
        static _name = "Thread";
        name;
        message = fields.One("Message", { inverse: "thread" });
        label = this.computed(() => {
            expect.step(`compute ${this.message?.body ?? "none"}`);
            return `label ${this.message?.body ?? "none"}`;
        });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        static _name = "Message";
        id;
        body;
        thread = fields.One("Thread", { inverse: "message" });
    }).register(localRegistry);
    const store = await start();
    const message = store.Message.insert({ id: 1, body: "hello" });
    const thread = store.Thread.insert({ name: "general", message });
    expect(thread.label).toBe("label hello");
    expect.verifySteps(["compute hello"]);
    thread.delete();
    expect(thread.label).toBe("label hello");
    message.body = "hi";
    expect(thread.label).toBe("label hello");
    expect.verifySteps([]);
    const unread = store.Thread.insert("unread");
    unread.delete();
    expect(unread.label).toBe(undefined);
    expect.verifySteps([]);
});

test("writing a computed warns and is dropped", async () => {
    patchWithCleanup(console, { warn: (msg) => expect.step(msg) });
    (class Thread extends Record {
        static id = "name";
        name;
        counter = 0;
        label = this.computed(() => `label ${this.counter}`);
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    expect(thread.label).toBe("label 0");
    store.Thread.insert({ name: "general", label: "from the server" });
    expect.verifySteps(["Thread.label is computed: dropping the write."]);
    expect(thread.label).toBe("label 0");
    thread.counter = 1;
    expect(thread.label).toBe("label 1");
});

test("an onChange registered in setup runs on the proxy and cleans up", async () => {
    (class Thread extends Record {
        static id = "name";
        static _name = "Thread";
        name;
        messages = fields.Many("Message", { inverse: "thread" });
        setup() {
            super.setup(...arguments);
            this.onChange(
                () => [this.messages.length],
                () => {
                    expect.step(`${this.messages.length} ${this.messages[0]?.body ?? ""}`);
                    return () => expect.step("cleanup");
                }
            );
        }
    }).register(localRegistry);
    (class Message extends Record {
        static id = "body";
        static _name = "Message";
        body;
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    await expect.waitForSteps(["0 "]);
    thread.messages.add("hello");
    await expect.waitForSteps(["cleanup", "1 hello"]);
    thread.delete();
    await expect.waitForSteps(["cleanup"]);
});

test("a computed is left out of toData()", async () => {
    (class Thread extends Record {
        static id = "name";
        name;
        label = this.computed(() => "a thread");
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    expect(thread.label).toBe("a thread");
    expect(Object.keys(thread.toData())).not.toInclude("label");
});

test("a model inheriting another reads its computeds", async () => {
    (class Thread extends Record {
        static id = "name";
        static _name = "Thread";
        name;
        counter = 0;
        channel = fields.One("Channel", { inverse: "thread" });
        label = this.computed(() => `label ${this.counter}`);
    }).register(localRegistry);
    (class Channel extends Record {
        static id = "name";
        static _name = "Channel";
        static _inherits = { Thread: "thread" };
        name;
        thread = fields.One("Thread", { inverse: "channel" });
    }).register(localRegistry);
    const store = await start();
    const channel = store.Channel.insert("general");
    channel.thread = { name: "general" };
    expect(channel.label).toBe("label 0");
    channel.thread.counter = 1;
    expect(channel.label).toBe("label 1");
});

test("a computed until stale should recompute value when stale", async () => {
    let ticks = 0;
    (class Thread extends Record {
        static id = "name";
        name;
        label = this.computedUntilStale(
            () => {
                expect.step(`compute ${ticks}`);
                return `label ${ticks}`;
            },
            () => 1000
        );
    }).register(localRegistry);
    const store = await start();
    const thread = store.Thread.insert("general");
    expect(thread.label).toBe("label 0");
    expect.verifySteps(["compute 0"]);
    ticks = 1;
    expect(thread.label).toBe("label 0");
    expect.verifySteps([]);
    await advanceTime(1000);
    expect(thread.label).toBe("label 1");
    expect.verifySteps(["compute 1"]);
});

test("a record made while the store is made reads the true store", async () => {
    localRegistry.remove("Store");
    (class TestStore extends Store {
        static _name = "Store";
        setup() {
            super.setup(...arguments);
            this.thread = { name: "boot" };
        }
        thread = fields.One("Thread");
    }).register(localRegistry);
    (class Thread extends Record {
        static id = "name";
        static _name = "Thread";
        name;
        messages = fields.Many("Message", { inverse: "thread" });
    }).register(localRegistry);
    (class Message extends Record {
        static id = "id";
        static _name = "Message";
        id;
        thread = fields.One("Thread", { inverse: "messages" });
    }).register(localRegistry);
    const store = await start();
    expect(store.thread.name).toBe("boot");
    expect(store.thread.messages._store).toBe(store);
});
