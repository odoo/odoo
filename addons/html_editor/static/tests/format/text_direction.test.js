import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { insertText, switchDirection } from "../_helpers/user_actions";
import { animationFrame } from "@odoo/hoot-mock";
import { press, queryAllTexts } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";
import { expectElementCount } from "../_helpers/ui_expectations";

test("should switch direction on a collapsed range", async () => {
    await testEditor({
        contentBefore: `<p>a[]b</p>`,
        stepFunction: switchDirection,
        contentAfter: `<p dir="rtl">a[]b</p>`,
    });
});

test("should switch direction on an uncollapsed range", async () => {
    await testEditor({
        contentBefore: `<p>a[b]c</p>`,
        stepFunction: switchDirection,
        contentAfter: `<p dir="rtl">a[b]c</p>`,
    });
});

test("should not switch direction of non-editable elements", async () => {
    await testEditor({
        contentBefore: `<p>[before</p><p contenteditable="false">noneditable</p><p>after]</p>`,
        stepFunction: switchDirection,
        contentAfter: `<p dir="rtl">[before</p><p contenteditable="false">noneditable</p><p dir="rtl">after]</p>`,
    });
});

test("should properly switch the direction of the single level list (ltr).", async () => {
    await testEditor({
        contentBefore: `<ul><li>a</li><li>b[]</li><li>c</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul dir="rtl"><li>a</li><li>b[]</li><li>c</li></ul>`,
    });
    await testEditor({
        contentBefore: `<ol><li>a</li><li>b[]</li><li>c</li></ol>`,
        stepFunction: switchDirection,
        contentAfter: `<ol dir="rtl"><li>a</li><li>b[]</li><li>c</li></ol>`,
    });
    await testEditor({
        contentBefore: `<ul class="o_checklist"><li>a</li><li>b[]</li><li>c</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul class="o_checklist" dir="rtl"><li>a</li><li>b[]</li><li>c</li></ul>`,
    });
});

test("should properly switch the direction of nested list (ltr).", async () => {
    await testEditor({
        contentBefore: `<ul><li><p>a[]</p><ul><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul dir="rtl"><li><p>a[]</p><ul dir="rtl"><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
    });
    await testEditor({
        contentBefore: `<ol><li><p>a[]</p><ol><li>b</li><li>c</li></ol></li><li>d</li></ol>`,
        stepFunction: switchDirection,
        contentAfter: `<ol dir="rtl"><li><p>a[]</p><ol dir="rtl"><li>b</li><li>c</li></ol></li><li>d</li></ol>`,
    });
    await testEditor({
        contentBefore: `<ul class="o_checklist"><li><p>a[]</p><ul class="o_checklist"><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul class="o_checklist" dir="rtl"><li><p>a[]</p><ul class="o_checklist" dir="rtl"><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
    });
    await testEditor({
        contentBefore: `<ul><li><p>a[]</p><ul class="o_checklist"><li><p>b</p><ol><li>g</li><li>e</li></ol></li><li>c</li></ul></li><li>d</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul dir="rtl"><li><p>a[]</p><ul class="o_checklist" dir="rtl"><li><p>b</p><ol dir="rtl"><li>g</li><li>e</li></ol></li><li>c</li></ul></li><li>d</li></ul>`,
    });
});

test("should properly switch the direction of the single level list (rtl).", async () => {
    await testEditor({
        contentBefore: `<ul dir="rtl"><li>a</li><li>b[]</li><li>c</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul><li>a</li><li>b[]</li><li>c</li></ul>`,
    });
    await testEditor({
        contentBefore: `<ol dir="rtl"><li>a</li><li>b[]</li><li>c</li></ol>`,
        stepFunction: switchDirection,
        contentAfter: `<ol><li>a</li><li>b[]</li><li>c</li></ol>`,
    });
    await testEditor({
        contentBefore: `<ul class="o_checklist" dir="rtl"><li>a</li><li>b[]</li><li>c</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul class="o_checklist"><li>a</li><li>b[]</li><li>c</li></ul>`,
    });
});

test("should properly switch the direction of nested list (rtl).", async () => {
    await testEditor({
        contentBefore: `<ul dir="rtl"><li><p>a[]</p><ul dir="rtl"><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul><li><p>a[]</p><ul><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
    });
    await testEditor({
        contentBefore: `<ol dir="rtl"><li><p>a[]</p><ol dir="rtl"><li>b</li><li>c</li></ol></li><li>d</li></ol>`,
        stepFunction: switchDirection,
        contentAfter: `<ol><li><p>a[]</p><ol><li>b</li><li>c</li></ol></li><li>d</li></ol>`,
    });
    await testEditor({
        contentBefore: `<ul class="o_checklist" dir="rtl"><li><p>a[]</p><ul class="o_checklist" dir="rtl"><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul class="o_checklist"><li><p>a[]</p><ul class="o_checklist"><li>b</li><li>c</li></ul></li><li>d</li></ul>`,
    });
    await testEditor({
        contentBefore: `<ul dir="rtl"><li><p>a[]</p><ul class="o_checklist" dir="rtl"><li><p>b</p><ol dir="rtl"><li>g</li><li>e</li></ol></li><li>c</li></ul></li><li>d</li></ul>`,
        stepFunction: switchDirection,
        contentAfter: `<ul><li><p>a[]</p><ul class="o_checklist"><li><p>b</p><ol><li>g</li><li>e</li></ol></li><li>c</li></ul></li><li>d</li></ul>`,
    });
});

test("should switch the direction from the powerbox", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>");
    await insertText(editor, "/Switchdirection");
    await animationFrame();
    expect(queryAllTexts(".o-we-command-name")).toEqual(["Switch direction"]);
    await expectElementCount(".o-we-powerbox", 1);
    await press("Enter");
    expect(getContent(el)).toBe(`<p dir="rtl">a[]</p>`);
    await insertText(editor, "/Switchdirection");
    await animationFrame();
    expect(queryAllTexts(".o-we-command-name")).toEqual(["Switch direction"]);
    await expectElementCount(".o-we-powerbox", 1);
    await press("Enter");
    expect(getContent(el)).toBe(`<p>a[]</p>`);
});
