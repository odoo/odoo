import { withSequence } from "@html_editor/utils/resource";
import { test, expect } from "@odoo/hoot";

test("withSequence throws if sequenceNumber is not a number", () => {
    for (const value of [undefined, null, "bonjour", { random: "object" }, true, false]) {
        expect(() => {
            withSequence(value, { a: "resource" });
        }).toThrow();
    }
});
