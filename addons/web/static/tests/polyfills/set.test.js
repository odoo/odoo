import { describe, expect, test } from "@odoo/hoot";

import { difference } from "@web/polyfills/set";

describe.current.tags("headless");

test("set difference", () => {
    function test(s1, s2) {
        let result;
        try {
            result = s1.difference(s2);
        } catch {
            expect(() => difference.call(s1, s2)).toThrow();
            return;
        }
        expect(difference.call(s1, s2)).toEqual(result);
    }
    test(new Set([1, 2, 3]), new Set([])); // [1, 2, 3]
    test(new Set([1, 2, 3]), new Set([1])); // [2, 3]
    test(new Set([1, 2, 3]), new Set([1, 2, 3])); // []
    test(new Set([1, 2, 3]), new Set([1, 2, 3, 5])); // []
    test(new Set([1, 2, 3]), new Set([5, 6])); // []
    test(new Set([]), new Set([1, 2, 3, 5])); // []

    test(new Set([])); // throws
    test(new Set([]), []); // throws
    test(new Set([]), {}); // throws
    test(new Set([]), 2); // throws
    test(new Set([1])); // throws
    test(new Set([1]), []); // throws
    test(new Set([1]), {}); // throws
    test(new Set([1]), 2); // throws
});
