import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import { expect, test } from "@odoo/hoot";

test("Convert with maximum float precision", () => {
    // The conversion might give a result off by exactly `Number.EPSILON`.
    // However `toBeCloseTo` only succeed if the result margin is strictly
    // less than the expected margin. So `2 * Number.EPSILON` is used.
    expect(convertNumericToUnit(1400, "ms", "s")).toBeCloseTo(1.4, {
        margin: 2 * Number.EPSILON,
    });
    expect(convertNumericToUnit(19, "px", "rem", getHtmlStyle(document))).toBe(1.1875);
});
