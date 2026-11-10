import { expect, test } from "@odoo/hoot";
import { getContrastRatio } from "@html_editor/utils/contrast";

test("computes the WCAG contrast ratio", () => {
    expect(getContrastRatio([0, 0, 0], [255, 255, 255])).toBe(21);
    expect(getContrastRatio([255, 255, 255], [0, 0, 0])).toBe(21);
    expect(getContrastRatio([119, 119, 119], [119, 119, 119])).toBe(1);
});
