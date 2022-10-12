/** @odoo-module **/

import { omit, pick, shallowEqual } from "@web/core/utils/objects";

QUnit.module("utils", () => {
    QUnit.module("Objects");

    QUnit.test("omit", function (assert) {
        assert.deepEqual(omit({}), {});
        assert.deepEqual(omit({}, "a"), {});
        assert.deepEqual(omit({ a: 1 }), { a: 1 });
        assert.deepEqual(omit({ a: 1 }, "a"), {});
        assert.deepEqual(omit({ a: 1, b: 2 }, "c", "a"), { b: 2 });
        assert.deepEqual(omit({ a: 1, b: 2 }, "b", "c"), { a: 1 });
    });

    QUnit.test("pick", function (assert) {
        assert.deepEqual(pick({}), {});
        assert.deepEqual(pick({}, "a"), {});
        assert.deepEqual(pick({ a: 3, b: "a", c: [] }, "a"), { a: 3 });
        assert.deepEqual(pick({ a: 3, b: "a", c: [] }, "a", "c"), { a: 3, c: [] });
        assert.deepEqual(pick({ a: 3, b: "a", c: [] }, "a", "b", "c"), { a: 3, b: "a", c: [] });

        // Non enumerable property
        class MyClass {
            get a() {
                return 1;
            }
        }
        const myClass = new MyClass();
        Object.defineProperty(myClass, "b", { enumerable: false, value: 2 });
        assert.deepEqual(pick(myClass, "a", "b"), { a: 1, b: 2 });
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
