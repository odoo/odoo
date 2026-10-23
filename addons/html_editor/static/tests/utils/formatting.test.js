import { isRedundantElement } from "@html_editor/utils/formatting";
import { describe, expect, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";

describe("isRedundantElement", () => {
    test("should detect semantic formatting tags as redundant when parent already has that visual formatting", () => {
        const [pElement] = insertTestHtml(
            `<p style="font-weight: bold;"><b>boldText</b><i>italicText</i><u>underlineText</u></p>`
        );
        const b = pElement.childNodes[0];
        const i = pElement.childNodes[1];
        const u = pElement.childNodes[2];

        expect(isRedundantElement(b)).toBe(true);
        expect(isRedundantElement(i)).toBe(false);
        expect(isRedundantElement(u)).toBe(false);
    });

    test("should detect nested small tags as redundant", () => {
        const [pElement] = insertTestHtml(`<p><small><small>small text</small></small></p>`);
        const outerSmall = pElement.firstChild;
        const innerSmall = outerSmall.firstChild;

        expect(isRedundantElement(outerSmall)).toBe(false);
        expect(isRedundantElement(innerSmall)).toBe(true);
    });

    test("should detect strong tag inside a visually-bold parent via class as redundant", () => {
        const [, pElement] = insertTestHtml(
            `<style>.boldClass { font-weight: bold; }</style><p class="boldClass"><strong>bold text</strong></p>`
        );
        const strong = pElement.firstChild;

        expect(isRedundantElement(strong)).toBe(true);
    });

    test("should evaluate empty span/font (0 attributes) as redundant only inside the exact same tag", () => {
        const [p1] = insertTestHtml(`<span><span>nested span</span></span>`);
        const innerSpan = p1.firstChild;
        expect(isRedundantElement(innerSpan)).toBe(true);

        const [p2] = insertTestHtml(`<font><span>nested different tag</span></font>`);
        const innerSpanInFont = p2.firstChild;
        expect(isRedundantElement(innerSpanInFont)).toBe(false);
    });

    test("should return false for span/font containing exotic attributes like id, data-*, lang", () => {
        const [pElement] = insertTestHtml(
            `<p style="color: red;"><span style="color: red;" id="my-span" data-test="123" lang="en">text</span></p>`
        );
        const span = pElement.firstChild;

        expect(isRedundantElement(span)).toBe(false);
    });

    test("should detect inline style matching parent computed style as redundant", () => {
        const [parentElement] = insertTestHtml(
            `<div style="color: rgb(255, 0, 0);"><span style="color: red;">text</span></div>`
        );
        const span = parentElement.firstChild;

        expect(isRedundantElement(span)).toBe(true);
    });

    test("should reject redundancy for intermediate style overrides", () => {
        const [outerFont] = insertTestHtml(
            `<font style="color: red;"><span style="color: blue;"><font style="color: red;">text</font></span></font>`
        );
        const middleSpan = outerFont.firstChild;
        const innerFont = middleSpan.firstChild;

        expect(isRedundantElement(middleSpan)).toBe(false);
        expect(isRedundantElement(innerFont)).toBe(false);
    });

    test("should detect color class already covered by ancestor span or font as redundant", () => {
        const [outerSpan] = insertTestHtml(
            `<span class="text-danger"><span class="text-danger">danger text</span></span>`
        );
        const innerSpan = outerSpan.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(true);
    });

    test("should reject redundancy when color class is overridden by a different class of same category on intermediate ancestor", () => {
        const [outerSpan] = insertTestHtml(
            `<span class="text-danger"><span class="text-primary"><span class="text-danger">text</span></span></span>`
        );
        const middleSpan = outerSpan.firstChild;
        const innerSpan = middleSpan.firstChild;

        expect(isRedundantElement(middleSpan)).toBe(false);
        expect(isRedundantElement(innerSpan)).toBe(false);
    });

    test("should return false when node classes are not all recognized color classes", () => {
        const [outerSpan] = insertTestHtml(
            `<span class="text-danger"><span class="text-danger my-custom-class">text</span></span>`
        );
        const innerSpan = outerSpan.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(false);
    });

    test("should require both inline styles and color classes to be redundant when both are present", () => {
        const [outerSpan] = insertTestHtml(
            `<span style="color: red;" class="text-danger"><span style="color: red;" class="text-primary">text</span></span>`
        );
        const innerSpan = outerSpan.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(false);
    });
});
