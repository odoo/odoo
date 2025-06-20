import { expect, test } from "@odoo/hoot";

import { concatenate } from "../src/functions";

/**
 * @hint missing import
 * @hint look at the test result in the UI
 */
test.todo("add", () => {
    expect(add(1, 2)).toBe(3);
    expect(add(0.1, 0.2)).not.toBe(0.3); // thx floating points
    expect(add("1", "2")).toBe(3);
});

/**
 * @hint `expect().toEqual()`
 */
test.todo("concatenate", () => {
    expect(concatenate([1], [2])).toBe([1, 2]);
});

/**
 * @hint `expect().toThrow()`
 */
test.todo("concatenate: error handling", () => {
    expect(concatenate("a", 1)).toEqual(new Error("Cannot concatenate non-iterable objects"));
});
