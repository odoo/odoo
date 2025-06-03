import { testEditor } from "../_helpers/editor";
import { test, before } from "@odoo/hoot";
import {
    setFontSize,
    splitBlock,
    toggleOrderedList,
    toggleUnorderedList,
} from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";

before(() => {
    return document.fonts.add(new FontFace(
        "Roboto",
        "url(/web/static/fonts/google/Roboto/Roboto-Regular.ttf)",
    )).ready;
});

test("should apply font-size to completely selected list item", async () => {
    await testEditor({
        styleContent: ':root { font: 14px Roboto }',
        contentBefore: "<ol><li>[abc]</li><li>def</li></ol>",
        stepFunction: setFontSize("56px"),
        contentAfter: `<ol style="padding-inline-start: 60px;"><li style="font-size: 56px;">[abc]</li><li>def</li></ol>`,
    });
});

test("should apply font-size to completely selected multiple list items", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def]</li></ul>",
        stepFunction: (editor) =>
            execCommand(editor, "formatFontSizeClassName", { className: "h2-fs" }),
        contentAfter: '<ul><li class="h2-fs">[abc</li><li class="h2-fs">def]</li></ul>',
    });
});

test("should apply font-size to completely selected and partially selected list items", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc</li><li>def</li><li>gh]i</li></ol>",
        stepFunction: setFontSize("18px"),
        contentAfter:
            '<ol><li style="font-size: 18px;">[abc</li><li style="font-size: 18px;">def</li><li><span style="font-size: 18px;">gh]</span>i</li></ol>',
    });
});

test("should apply font-size to completely selected list items and paragraph tag", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def</li></ul><p>ghi]</p>",
        stepFunction: (editor) =>
            execCommand(editor, "formatFontSizeClassName", { className: "h2-fs" }),
        contentAfter: `<ul><li class="h2-fs">[abc</li><li class="h2-fs">def</li></ul><p><span class="h2-fs">ghi]</span></p>`,
    });
});

test("should carry list item font-size to new list item", async () => {
    await testEditor({
        contentBefore: '<ol><li>abc</li><li style="font-size: 18px;">def[]</li></ol>',
        stepFunction: splitBlock,
        contentAfter:
            '<ol><li>abc</li><li style="font-size: 18px;">def</li><li style="font-size: 18px;">[]<br></li></ol>',
    });
});

test("should carry list item font-size to new list item (2)", async () => {
    await testEditor({
        contentBefore: '<ul><li class="h2-fs">[]abc</li><li>def</li></ul>',
        stepFunction: splitBlock,
        contentAfter: `<ul><li class="h2-fs"><br></li><li class="h2-fs">[]abc</li><li>def</li></ul>`,
    });
});

test("should carry font-size of paragraph to list item", async () => {
    await testEditor({
        contentBefore: '<p><span style="font-size: 18px;">[]abc</span></p>',
        stepFunction: toggleUnorderedList,
        contentAfter: '<ul><li style="font-size: 18px;">[]abc</li></ul>',
    });
});

test("should carry font-size of paragraph to list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li class="h3-fs">abc</li></ol><p><span class="h2-fs">[]def</span></p><ol><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter: `<ol><li class="h3-fs">abc</li><li class="h2-fs">[]def</li><li>ghi</li></ol>`,
    });
});

test("should carry font-size of paragraph to list item (3)", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="font-size: 18px;">abc</li></ul><p>[]def</p><ul><li style="font-size: 18px;">ghi</li></ul>',
        stepFunction: toggleUnorderedList,
        contentAfter:
            '<ul><li style="font-size: 18px;">abc</li><li>[]def</li><li style="font-size: 18px;">ghi</li></ul>',
    });
});

test("should carry font-size of list item to paragraph", async () => {
    await testEditor({
        contentBefore: '<ol><li style="font-size: 18px;">[]abc</li><li>def</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter: '<p><span style="font-size: 18px;">[]abc</span></p><ol><li>def</li></ol>',
    });
});

test("should carry font-size of list item to paragraph (2)", async () => {
    await testEditor({
        contentBefore:
            '<ul><li class="h2-fs">abc</li><li class="h2-fs">[]def</li><li>ghi</li></ul>',
        stepFunction: toggleUnorderedList,
        contentAfter: `<ul><li class="h2-fs">abc</li></ul><p><span class="h2-fs">[]def</span></p><ul><li>ghi</li></ul>`,
    });
});

test("should carry font-size of list item to paragraph (3)", async () => {
    await testEditor({
        contentBefore: '<ol><li style="font-size: 18px;">abc</li><li>[]def</li><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li style="font-size: 18px;">abc</li></ol><p>[]def</p><ol><li>ghi</li></ol>',
    });
});

test("should carry font-size of list item to paragraph (4)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px;">abc<span style="font-size: 32px;">def</span>ghi[]</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<p><span style="font-size: 18px;">abc<span style="font-size: 32px;">def</span>ghi[]</span></p>',
    });
});

test("should keep list item font-size on toggling list twice", async () => {
    await testEditor({
        styleContent: 'ol { font: 14px Roboto }',
        contentBefore:
            '<ol><li style="font-size: 18px;">[abc</li><li style="font-size: 32px;">def]</li></ol>',
        stepFunction: (editor) => {
            toggleOrderedList(editor);
            toggleOrderedList(editor);
        },
        contentAfter: `<ol style="padding-inline-start: 34px;"><li style="font-size: 18px;">[abc</li><li style="font-size: 32px;">def]</li></ol>`,
    });
});

test("should change font-size of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="font-size: 18px;">[abc]</li><li style="font-size: 18px;">ghi</li></ul>',
        stepFunction: setFontSize("32px"),
        contentAfter: `<ul><li style="font-size: 32px;">[abc]</li><li style="font-size: 18px;">ghi</li></ul>`,
    });
});

test("should change font-size of a list item (2)", async () => {
    await testEditor({
        styleContent: 'ol { font: 14px Roboto }',
        contentBefore:
            '<ol><li style="font-size: 18px;">[abc</li><li style="font-size: 18px;">ghi]</li></ol>',
        stepFunction: setFontSize("32px"),
        contentAfter: `<ol style="padding-inline-start: 34px;"><li style="font-size: 32px;">[abc</li><li style="font-size: 32px;">ghi]</li></ol>`,
    });
});

test("should change font-size of subpart of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px;">a[b]c</li><li style="font-size: 18px;">ghi</li></ol>',
        stepFunction: setFontSize("32px"),
        contentAfter:
            '<ol><li style="font-size: 18px;">a<span style="font-size: 32px;">[b]</span>c</li><li style="font-size: 18px;">ghi</li></ol>',
    });
});

test("should change font-size of subpart of a list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px;">a[bc</li><li style="font-size: 18px;">gh]i</li></ol>',
        stepFunction: setFontSize("32px"),
        contentAfter:
            '<ol><li style="font-size: 18px;">a<span style="font-size: 32px;">[bc</span></li><li style="font-size: 18px;"><span style="font-size: 32px;">gh]</span>i</li></ol>',
    });
});

test("should pad list based on font-size", async () => {
    const className = "h2-fs";
    await testEditor({
        contentBefore: "<ol><li>[a]</li></ol>",
        stepFunction: (editor) => execCommand(editor, "formatFontSizeClassName", { className }),
        contentAfter: `<ol><li class="${className}">[a]</li></ol>`,
    });
});

test("should pad list based on font-size (2)", async () => {
    await testEditor({
        styleContent: 'ol { font: 14px Roboto }',
        contentBefore: `<span style="font-size: 56px">[a]</span>`,
        stepFunction: toggleOrderedList,
        contentAfter: `<ol style="padding-inline-start: 60px;"><li style="font-size: 56px;">[]a</li></ol>`,
    });
});
