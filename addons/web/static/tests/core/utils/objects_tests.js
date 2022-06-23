/** @odoo-module **/

import { pluck, shallowEqual } from "@web/core/utils/objects";

QUnit.module("utils", () => {
    QUnit.module("Objects");

    QUnit.test("pluck", function (assert) {
        assert.deepEqual(pluck({}), {});
        assert.deepEqual(pluck({}, "a"), {});
        assert.deepEqual(pluck({ a: 3, b: "a", c: [] }, "a"), { a: 3 });
        assert.deepEqual(pluck({ a: 3, b: "a", c: [] }, "a", "c"), { a: 3, c: [] });
        assert.deepEqual(pluck({ a: 3, b: "a", c: [] }, "a", "b", "c"), { a: 3, b: "a", c: [] });
    });

    QUnit.test("shallowEqual: simple valid cases", function (assert) {
        assert.ok(shallowEqual({}, {}));
        assert.ok(shallowEqual({ a: 1 }, { a: 1 }));
        assert.ok(shallowEqual({ a: 1, b: "x" }, { b: "x", a: 1 }));
    });

    QUnit.test("shallowEqual: simple invalid cases", function (assert) {
        assert.notOk(shallowEqual({ a: 1 }, { a: 2 }));
        assert.notOk(shallowEqual({}, { a: 2 }));
        assert.notOk(shallowEqual({ a: 1 }, {}));
    });

    QUnit.test("shallowEqual: objects with non primitive values", function (assert) {
        const obj = { x: "y" };
        assert.ok(shallowEqual({ a: obj }, { a: obj }));
        assert.notOk(shallowEqual({ a: { x: "y" } }, { a: { x: "y" } }));

        const arr = ["x", "y", "z"];
        assert.ok(shallowEqual({ a: arr }, { a: arr }));
        assert.notOk(shallowEqual({ a: ["x", "y", "z"] }, { a: ["x", "y", "z"] }));

        const fn = () => {};
        assert.ok(shallowEqual({ a: fn }, { a: fn }));
        assert.notOk(shallowEqual({ a: () => {} }, { a: () => {} }));
    });
});
