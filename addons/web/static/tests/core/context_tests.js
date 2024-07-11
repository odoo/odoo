/** @odoo-module **/

import { evalPartialContext, makeContext } from "@web/core/context";

QUnit.module("Context", {}, () => {
    QUnit.module("makeContext");

    QUnit.test("return empty context", (assert) => {
        assert.deepEqual(makeContext([]), {});
    });

    QUnit.test("duplicate a context", (assert) => {
        const ctx1 = { a: 1 };
        const ctx2 = makeContext([ctx1]);
        assert.notStrictEqual(ctx1, ctx2);
        assert.deepEqual(ctx1, ctx2);
    });

    QUnit.test("can accept undefined or empty string", (assert) => {
        assert.deepEqual(makeContext([undefined]), {});
        assert.deepEqual(makeContext([{ a: 1 }, undefined, { b: 2 }]), { a: 1, b: 2 });
        assert.deepEqual(makeContext([""]), {});
        assert.deepEqual(makeContext([{ a: 1 }, "", { b: 2 }]), { a: 1, b: 2 });
    });

    QUnit.test("evaluate strings", (assert) => {
        assert.deepEqual(makeContext(["{'a': 33}"]), { a: 33 });
    });

    QUnit.test("evaluated context is used as evaluation context along the way", (assert) => {
        assert.deepEqual(makeContext([{ a: 1 }, "{'a': a + 1}"]), { a: 2 });
        assert.deepEqual(makeContext([{ a: 1 }, "{'b': a + 1}"]), { a: 1, b: 2 });
        assert.deepEqual(makeContext([{ a: 1 }, "{'b': a + 1}", "{'c': b + 1}"]), {
            a: 1,
            b: 2,
            c: 3,
        });
        assert.deepEqual(makeContext([{ a: 1 }, "{'b': a + 1}", "{'a': b + 1}"]), { a: 3, b: 2 });
    });

    QUnit.test("initial evaluation context", (assert) => {
        assert.deepEqual(makeContext(["{'a': a + 1}"], { a: 1 }), { a: 2 });
        assert.deepEqual(makeContext(["{'b': a + 1}"], { a: 1 }), { b: 2 });
    });

    QUnit.module("evalPartialContext");

    QUnit.test("static contexts", (assert) => {
        assert.deepEqual(evalPartialContext("{}", {}), {});
        assert.deepEqual(evalPartialContext("{'a': 1}", {}), { a: 1 });
        assert.deepEqual(evalPartialContext("{'a': 'b'}", {}), { a: "b" });
        assert.deepEqual(evalPartialContext("{'a': true}", {}), { a: true });
        assert.deepEqual(evalPartialContext("{'a': None}", {}), { a: null });
    });

    QUnit.test("complete dynamic contexts", (assert) => {
        assert.deepEqual(evalPartialContext("{'a': a, 'b': 1}", { a: 2 }), { a: 2, b: 1 });
    });

    QUnit.test("partial dynamic contexts", (assert) => {
        assert.deepEqual(evalPartialContext("{'a': a}", {}), {});
        assert.deepEqual(evalPartialContext("{'a': a, 'b': 1}", {}), { b: 1 });
        assert.deepEqual(evalPartialContext("{'a': a, 'b': b}", { a: 2 }), { a: 2 });
    });

    QUnit.test("value of type obj (15)", (assert) => {
        assert.deepEqual(evalPartialContext("{'a': a.b.c}", {}), {});
        assert.deepEqual(evalPartialContext("{'a': a.b.c}", { a: {} }), {});
        assert.deepEqual(evalPartialContext("{'a': a.b.c}", { a: { b: { c: 2 } } }), { a: 2 });
    });

    QUnit.test("value of type op (14)", (assert) => {
        assert.deepEqual(evalPartialContext("{'a': a + 1}", {}), {});
        assert.deepEqual(evalPartialContext("{'a': a + b}", {}), {});
        assert.deepEqual(evalPartialContext("{'a': a + b}", { a: 2 }), {});
        assert.deepEqual(evalPartialContext("{'a': a + 1}", { a: 2 }), { a: 3 });
        assert.deepEqual(evalPartialContext("{'a': a + b}", { a: 2, b: 3 }), { a: 5 });
    });
});
