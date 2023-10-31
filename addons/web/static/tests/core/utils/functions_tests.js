/** @odoo-module **/

import { memoize } from "@web/core/utils/functions";

QUnit.module("utils", () => {
    QUnit.module("Functions");

    QUnit.test("memoize", function (assert) {
        let callCount = 0;
        let lastReceivedArgs;
        const func = function () {
            lastReceivedArgs = [...arguments];
            return callCount++;
        };
        const memoized = memoize(func);
        const firstValue = memoized("first");
        assert.equal(callCount, 1, "Memoized function was called once to fill the cache");
        assert.equal(lastReceivedArgs, "first", "Memoized function received the correct argument");
        const secondValue = memoized("first");
        assert.equal(
            callCount,
            1,
            "Subsequent calls to memoized function with the same argument do not call the original function again"
        );
        assert.equal(
            firstValue,
            secondValue,
            "Subsequent call to memoized function with the same argument returns the same value"
        );

        const thirdValue = memoized();
        assert.equal(
            callCount,
            2,
            "Subsequent calls to memoized function with a different argument call the original function again"
        );
        const fourthValue = memoized();
        assert.equal(
            thirdValue,
            fourthValue,
            "Memoization also works with no first argument as a key"
        );
        assert.equal(
            callCount,
            2,
            "Subsequent calls to memoized function with no first argument do not call the original function again"
        );

        memoized(1, 2, 3);
        assert.equal(callCount, 3);
        assert.deepEqual(
            lastReceivedArgs,
            [1, 2, 3],
            "Arguments after the first one are passed through correctly"
        );
        memoized(1, 20, 30);
        assert.equal(
            callCount,
            3,
            "Subsequent calls to memoized function with more than one argument do not call the original function again even if the arguments other than the first have changed"
        );
    });

    QUnit.test("memoized function inherit function name if possible", function (assert) {
        const memoized1 = memoize(function test() {});
        assert.strictEqual(memoized1.name, "test (memoized)");

        const memoized2 = memoize(function () {});
        assert.strictEqual(memoized2.name, "memoized");
    });
});
