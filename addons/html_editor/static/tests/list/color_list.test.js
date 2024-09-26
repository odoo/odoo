import { click, waitFor } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "../_helpers/editor";
import { expect, test } from "@odoo/hoot";
import {
    setColor,
    setFontSize,
    splitBlock,
    toggleOrderedList,
    toggleUnorderedList,
} from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { animationFrame } from "@odoo/hoot-mock";

test("should carry list item color to new list item", async () => {
    await testEditor({
        contentBefore: '<ol><li>abc</li><li style="color: rgb(255, 0, 0);">def[]</li></ol>',
        stepFunction: splitBlock,
        contentAfter:
            '<ol><li>abc</li><li style="color: rgb(255, 0, 0);">def</li><li style="color: rgb(255, 0, 0);">[]<br></li></ol>',
    });
});

test("should carry list color to new list item (2)", async () => {
    await testEditor({
        contentBefore: '<ol><li style="color: rgb(255, 0, 0);">[]abc</li><li>def</li></ol>',
        stepFunction: splitBlock,
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);"><br></li><li style="color: rgb(255, 0, 0);">[]abc</li><li>def</li></ol>',
    });
});

test("should carry color of paragraph to list item", async () => {
    await testEditor({
        contentBefore: '<p><font style="color: rgb(255, 0, 0);">[]abc</font></p>',
        stepFunction: toggleOrderedList,
        contentAfter: '<ol><li style="color: rgb(255, 0, 0);">[]abc</li></ol>',
    });
});

test("should carry color of paragraph to list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li></ol><p><font style="color: rgb(0, 0, 255);">[]def</font></p><ol><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li><li style="color: rgb(0, 0, 255);">[]def</li><li>ghi</li></ol>',
    });
});

test("should carry color of paragraph to list item (2) (3)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li></ol><p>[]def</p><ol><li style="color: rgb(255, 0, 0);">ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li><li>[]def</li><li style="color: rgb(255, 0, 0);">ghi</li></ol>',
    });
});

test("should carry color of list item to paragraph", async () => {
    await testEditor({
        contentBefore: '<ol><li style="color: rgb(255, 0, 0);">[]abc</li><li>def</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<p><font style="color: rgb(255, 0, 0);">[]abc</font></p><ol><li>def</li></ol>',
    });
});

test("should carry color of list item to paragraph (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li><li style="color: rgb(0, 0, 255);">[]def</li><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li></ol><p><font style="color: rgb(0, 0, 255);">[]def</font></p><ol><li>ghi</li></ol>',
    });
});

test("should carry color of list item to paragraph (3)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li><li>[]def</li><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">abc</li></ol><p>[]def</p><ol><li>ghi</li></ol>',
    });
});

test("should keep list item color on toggling list twice", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(0, 0, 255);">def]</li></ol>',
        stepFunction: (editor) => {
            toggleOrderedList(editor);
            toggleOrderedList(editor);
        },
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(0, 0, 255);">def]</li></ol>',
    });
});

test("remove color from list item", async () => {
    const { el } = await setupEditor(
        `<ol><li style="color: rgb(255, 0, 0);">abc</li><li style="color: rgb(255, 0, 0);">[ghi]</li></ol>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1); // toolbar open
    expect(".btn[name='remove_format']").toHaveCount(1); // remove format
    expect(".btn[name='remove_format']").not.toHaveClass("disabled"); // remove format button should not be disabled
    click(".btn[name='remove_format']");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<ol><li style="color: rgb(255, 0, 0);">abc</li><li style="">[ghi]</li></ol>`
    );
});

test("should apply color to completely selected list item", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc]</li><li>ghi</li></ol>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: '<ol><li style="color: rgb(255, 0, 0);">[abc]</li><li>ghi</li></ol>',
    });
});

test("should apply color to completely selected multiple list items", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc</li><li>ghi]</li></ol>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">ghi]</li></ol>',
    });
});

test("should change color of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">[abc]</li><li style="color: rgb(255, 0, 0);">ghi</li></ol>',
        stepFunction: setColor("rgb(0, 0, 255)", "color"),
        contentAfter:
            '<ol><li style="color: rgb(0, 0, 255);">[abc]</li><li style="color: rgb(255, 0, 0);">ghi</li></ol>',
    });
});

test("should change color of a list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">ghi]</li></ol>',
        stepFunction: setColor("rgb(0, 0, 255)", "color"),
        contentAfter:
            '<ol><li style="color: rgb(0, 0, 255);">[abc</li><li style="color: rgb(0, 0, 255);">ghi]</li></ol>',
    });
});

test("should change color of subpart of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">a[b]c</li><li style="color: rgb(255, 0, 0);">ghi</li></ol>',
        stepFunction: setColor("rgb(0, 0, 255)", "color"),
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">a<font style="color: rgb(0, 0, 255);">[b]</font>c</li><li style="color: rgb(255, 0, 0);">ghi</li></ol>',
    });
});

test("should change color of subpart of a list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">a[bc</li><li style="color: rgb(255, 0, 0);">gh]i</li></ol>',
        stepFunction: setColor("rgb(0, 0, 255)", "color"),
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">a<font style="color: rgb(0, 0, 255);">[bc</font></li><li style="color: rgb(255, 0, 0);"><font style="color: rgb(0, 0, 255);">gh]</font>i</li></ol>',
    });
});

// @todo: write test case for remove format on list partially selected also find something better than color: initial.

test("should apply font size to list if completely selected", async () => {
    await testEditor({
        contentBefore: `<ul><li>[abc</li><li>def]</li></ul>`,
        stepFunction: setFontSize("18px"),
        contentAfter: `<ul style="font-size: 18px; list-style-position: inside;"><li>[abc</li><li>def]</li></ul>`,
    });
});

test("should not apply font size to list itself if partially selected", async () => {
    await testEditor({
        contentBefore: `<ul><li>[abc]</li><li>def</li></ul>`,
        stepFunction: setFontSize("18px"),
        contentAfter: `<ul><li><span style="font-size: 18px;">[abc]</span></li><li>def</li></ul>`,
    });
});

test("should carry font size of list to paragraph", async () => {
    await testEditor({
        contentBefore: `<ul style="font-size: 20px;"><li>[]abc</li><li>def</li></ul>`,
        stepFunction: toggleUnorderedList,
        contentAfter: `<p><span style="font-size: 20px;">[]abc</span></p><ul style="font-size: 20px;"><li>def</li></ul>`,
    });
});

test("should carry font class of list to paragraph", async () => {
    await testEditor({
        contentBefore: `<ul class="display-2-fs"><li>[]abc</li><li>def</li></ul>`,
        stepFunction: toggleUnorderedList,
        contentAfter: `<p><span class="display-2-fs">[]abc</span></p><ul class="display-2-fs"><li>def</li></ul>`,
    });
});
