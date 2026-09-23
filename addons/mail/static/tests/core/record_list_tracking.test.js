// @ts-check
import { defineMailModels, start as start2 } from "@mail/../tests/mail_test_helpers";
import { makeStore, Record, Store } from "@mail/core/common/record";
import { fields } from "@mail/model/misc";
import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, toRaw, useState, xml } from "@odoo/owl";
import { mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");
defineMailModels();

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
    const env = await start2();
    return env.services.store;
}

/** @param {(list: any) => string} read */
function defineModels(read) {
    (class Contact extends Record {
        static id = "name";
        name;
        tasks = fields.Many(/** @type {string} */ ("Task"), { inverse: "contact" });
        summary = fields.Attr("", {
            /** @this {Contact} */
            compute() {
                return read(this.tasks);
            },
        });
    }).register(localRegistry);
    (class Task extends Record {
        static id = "name";
        name;
        label = fields.Attr("");
        contact = fields.One(/** @type {string} */ ("Contact"), { inverse: "tasks" });
    }).register(localRegistry);
}

const READERS = {
    map: (list) => list.map((t) => t.label).join(","),
    filter: (list) =>
        list
            .filter((t) => t.label !== "")
            .map((t) => t.label)
            .join(","),
    find: (list) => list.find((t) => t.label !== "")?.label ?? "",
    findLast: (list) => list.findLast((t) => t.label !== "")?.label ?? "",
    findIndex: (list) => String(list.findIndex((t) => t.label === "hit")),
    findLastIndex: (list) => String(list.findLastIndex((t) => t.label === "hit")),
    some: (list) => String(list.some((t) => t.label === "hit")),
    every: (list) => String(list.every((t) => t.label === "hit")),
    forEach: (list) => {
        let acc = "";
        list.forEach((t) => (acc += t.label));
        return acc;
    },
    reduce: (list) => list.reduce((acc, t) => acc + t.label, ""),
    slice: (list) =>
        list
            .slice(0)
            .map((t) => t.label)
            .join(","),
    iterator: (list) => [...list].map((t) => t.label).join(","),
    concat: (list) =>
        list
            .concat([])
            .map((t) => t.label)
            .join(","),
    at: (list) => list.at(0)?.label ?? "",
};

for (const [name, read] of Object.entries(READERS)) {
    test(`compute reading a related field through list.${name}() re-runs on that field's change`, async () => {
        defineModels(read);
        const store = await start();
        const john = store.Contact.insert("John");
        const t1 = store.Task.insert({ name: "t1", label: "a" });
        john.tasks.add(t1);
        const before = john.summary;
        t1.label = "hit";
        expect(john.summary).not.toBe(before, {
            message: `list.${name}() lost dependency tracking on the related record`,
        });
    });
}

test("component reading related fields through a list read method re-renders", async () => {
    defineModels((list) => list.map((t) => t.label).join(","));
    const store = await start();
    const john = store.Contact.insert("John");
    const t1 = store.Task.insert({ name: "t1", label: "a" });
    john.tasks.add(t1);

    class Labels extends Component {
        static props = ["contact"];
        static template = xml`
            <div class="labels"><t t-foreach="this.labels" t-as="l" t-key="l_index"><span t-out="l"/></t></div>`;
        setup() {
            this.contact = useState(this.props.contact);
        }
        get labels() {
            return this.contact.tasks.map((t) => t.label);
        }
    }
    await mountWithCleanup(Labels, { props: { contact: john } });
    expect(".labels").toHaveText("a");
    t1.label = "b";
    await animationFrame();
    expect(".labels").toHaveText("b", {
        message: "template lost dependency tracking on the related record",
    });
});

test("off the reactive path both maps resolve to the very same record", async () => {
    defineModels((list) => list.map((t) => t.label).join(","));
    {
        const store = await start();
        const john = store.Contact.insert("John");
        const t1 = store.Task.insert({ name: "t1", label: "a" });
        john.tasks.add(t1);
        const reactiveMap = toRaw(john)._raw.tasks._store.recordByLocalId;
        const rawMap = toRaw(reactiveMap);
        expect(rawMap).not.toBe(reactiveMap, {
            message: "the maps are distinct objects",
        });
        const localId = toRaw(t1)._raw.localId;
        expect(rawMap.get(localId)).toBe(reactiveMap.get(localId), {
            message: "same record instance through either map",
        });
        expect(rawMap.get(localId)).toBe(toRaw(t1)._raw._proxy);
    }
});
