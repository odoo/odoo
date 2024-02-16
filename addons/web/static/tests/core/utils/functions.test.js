import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { memoize, uniqueId } from "@web/core/utils/functions";

describe.current.tags("headless");

test("memoize", () => {
    let callCount = 0;
    let lastReceivedArgs;
    const func = function () {
        lastReceivedArgs = [...arguments];
        return callCount++;
    };
    const memoized = memoize(func);
    const firstValue = memoized("first");
    expect(callCount).toBe(1);
    expect(lastReceivedArgs).toEqual(["first"]);
    const secondValue = memoized("first");
    // Subsequent calls to memoized function with the same argument do not call the original function again
    expect(callCount).toBe(1);
    // Subsequent call to memoized function with the same argument returns the same value
    expect(firstValue).toBe(secondValue);
    const thirdValue = memoized();
    // Subsequent calls to memoized function with a different argument call the original function again
    expect(callCount).toBe(2);
    const fourthValue = memoized();
    // Memoization also works with no first argument as a key
    expect(thirdValue).toBe(fourthValue);
    // Subsequent calls to memoized function with no first argument do not call the original function again
    expect(callCount).toBe(2);
    memoized(1, 2, 3);
    expect(callCount).toBe(3);
    // Arguments after the first one are passed through correctly
    expect(lastReceivedArgs).toEqual([1, 2, 3]);
    memoized(1, 20, 30);
    // Subsequent calls to memoized function with more than one argument do not call the original function again even if the arguments other than the first have changed
    expect(callCount).toBe(3);
});

test("memoized function inherit function name if possible", () => {
    const memoized1 = memoize(function test() {});
    expect(memoized1.name).toBe("test (memoized)");
    const memoized2 = memoize(function () {});
    expect(memoized2.name).toBe("memoized");
});

test("uniqueId", () => {
    patchWithCleanup(uniqueId, { nextId: 0 });
    expect(uniqueId("test_")).toBe("test_1");
    expect(uniqueId("bla")).toBe("bla2");
    expect(uniqueId("test_")).toBe("test_3");
    expect(uniqueId("bla")).toBe("bla4");
    expect(uniqueId("test_")).toBe("test_5");
    expect(uniqueId("test_")).toBe("test_6");
    expect(uniqueId("bla")).toBe("bla7");
});
