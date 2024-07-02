import { expect, test } from "@odoo/hoot";

import { add, concatenate } from "../src/functions";

/**
 * @hint missing import
 * @hint look at the test result in the UI
 */
test("add", () => {
    expect(add(1, 2)).toBe(3);
    expect(add(0.1, 0.2)).not.toBe(0.3); // thx floating points
    expect(add("1", "2")).toBe("12");
});

/**
 * @hint `expect().toEqual()`
 */
test("concatenate", () => {
    expect(concatenate([1], [2])).toEqual([1, 2]);
});

/**
 * @hint `expect().toThrow()`
 */
test("concatenate: error handling", () => {
    expect(() => concatenate("a", 1)).toThrow(new Error("Cannot concatenate non-iterable objects"));
});
