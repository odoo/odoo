/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";
import { BaseStore, makeStore } from "@mail/core/common/store_service";

import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "@web/../tests/helpers/mock_env";

const serviceRegistry = registry.category("services");

let start;
QUnit.module("record", {
    beforeEach() {
        serviceRegistry.add("store", { start: (env) => makeStore(env) });
        clearRegistryWithCleanup(modelRegistry);
        Record.register();
        ({ Store: class extends BaseStore {} }).Store.register();
        start = async () => await makeTestEnv();
    },
});

QUnit.test("Assign & Delete on fields with inverses", async (assert) => {
    (class A extends Record {
        static id = "id";
        id;
        b = Record.one("B", { inverse: "a" });
        c = Record.one("C", { inverse: "aa" });
        dd = Record.many("D", { inverse: "aa" });
    }).register();
    (class B extends Record {
        static id = "id";
        id;
        a = Record.one("A");
    }).register();
    (class C extends Record {
        static id = "id";
        id;
        aa = Record.many("A");
    }).register();
    (class D extends Record {
        static id = "id";
        id;
        aa = Record.many("A");
    }).register();
    const env = await start();
    const a = env.services.store.A.insert("a");
    const b = env.services.store.B.insert("b");
    const c1 = env.services.store.C.insert("c1");
    const c2 = env.services.store.C.insert("c2");
    const d1 = env.services.store.D.insert("d1");
    const d2 = env.services.store.D.insert("d2");
    // Assign on fields should adapt inverses
    Object.assign(a, { b, c: [["ADD", c1]], dd: [d1, d2] });
    assert.ok(a.b.eq(b));
    assert.ok(b.a.eq(a));
    assert.ok(a.c.eq(c1));
    assert.ok(a.in(c1.aa));
    assert.ok(d1.in(a.dd));
    assert.ok(d2.in(a.dd));
    assert.ok(a.in(d1.aa));
    assert.ok(a.in(d2.aa));
    // add() should adapt inverses
    c2.aa.add(a);
    assert.ok(a.in(c2.aa));
    assert.ok(a.c.eq(c2));
    // delete should adapt inverses
    c2.aa.delete(a);
    assert.notOk(a.in(c2.aa));
    assert.notOk(a.c);
    // Deletion removes all relations
    a.delete();
    assert.notOk(a.b);
    assert.notOk(b.a);
    assert.notOk(a.in(c1.aa));
    assert.notOk(d1.in(a.dd));
    assert.notOk(d2.in(a.dd));
    assert.notOk(a.in(d1.aa));
    assert.notOk(a.in(d2.aa));
});
