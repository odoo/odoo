import { convertNumericToUnit } from "@html_editor/utils/formatting";
import { describe, expect, test } from "@odoo/hoot";

describe("NumericToUnitConverter", () => {
    test("displays the correct value (no floating point precision error)", () => {
        expect(convertNumericToUnit(1400, "ms", "s")).toBe(1.4);
    });
});
