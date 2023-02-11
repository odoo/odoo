/** @odoo-module **/

import { shallowEqual } from "@web/core/utils/objects";

QUnit.module("utils", () => {
    QUnit.module("Objects");

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
