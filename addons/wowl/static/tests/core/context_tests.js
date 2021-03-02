/** @odoo-module **/

import { makeContext } from "../../src/core/context";

QUnit.module("utils", {}, () => {
  QUnit.module("makeContext");

  QUnit.test("return empty context", (assert) => {
    assert.deepEqual(makeContext(), {});
  });

  QUnit.test("duplicate a context", (assert) => {
    const ctx1 = { a: 1 };
    const ctx2 = makeContext(ctx1);
    assert.notStrictEqual(ctx1, ctx2);
    assert.deepEqual(ctx1, ctx2);
  });

  QUnit.test("can accept undefined", (assert) => {
    assert.deepEqual(makeContext(undefined), {});
    assert.deepEqual(makeContext({ a: 1 }, undefined, { b: 2 }), { a: 1, b: 2 });
  });

  QUnit.test("evaluate strings", (assert) => {
    assert.deepEqual(makeContext("{'a': 33}"), { a: 33 });
    assert.deepEqual(makeContext({ a: 1 }, "{'b': a + 1}"), { a: 1, b: 2 });
  });
});
