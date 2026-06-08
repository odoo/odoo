import { expect, test } from "@odoo/hoot";
import { closest } from "@web/core/utils/ui";

test("Closest function works correctly with nested elements", () => {
    const inner = {
        getBoundingClientRect: () => ({ x: 50, y: 50, width: 50, height: 50 }),
    };
    const outer = {
        getBoundingClientRect: () => ({ x: 0, y: 0, width: 200, height: 200 }),
    };
    const pos = { x: 60, y: 60 };
    const result = closest([inner, outer], pos);
    expect(result).toBe(inner);
});

test("Closest function finds the correct element", () => {
    const inner = {
        getBoundingClientRect: () => ({ x: 50, y: 50, width: 50, height: 50 }),
    };
    const outer = {
        getBoundingClientRect: () => ({ x: 0, y: 0, width: 200, height: 200 }),
    };
    const pos = { x: 10, y: 10, width: 40, height: 40 };
    const result = closest([inner, outer], pos);
    expect(result).toBe(outer);
});

test("Closest function returns the right element when position is right next to it", () => {
    const el1 = {
        getBoundingClientRect: () => ({ x: 50, y: 50, width: 100, height: 100 }),
    };
    const el2 = {
        getBoundingClientRect: () => ({ x: 0, y: 0, width: 300, height: 200 }),
    };
    const pos = { x: 49, y: 49, width: 20, height: 20 };
    const result = closest([el1, el2], pos);
    expect(result).toBe(el1);
});
