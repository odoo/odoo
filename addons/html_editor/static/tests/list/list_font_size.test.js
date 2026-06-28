import { testEditor } from "../_helpers/editor";
import { test, before } from "@odoo/hoot";
import {
    setFontSize,
    setFontSizeClassName,
    splitBlock,
    toggleOrderedList,
    toggleUnorderedList,
} from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";
import { unformat } from "../_helpers/format";
import { nodeSize } from "@html_editor/utils/position";

before(async () => {
    const font = new FontFace("Roboto", "url(/web/static/fonts/google/Roboto/Roboto-Regular.ttf)");
    await font.load();
    document.fonts.add(font);
    await document.fonts.ready;
});

test.tags("font-dependent");
test("should apply font-size to completely selected list item (1)", async () => {
    await testEditor({
        styleContent: ":root { font: 14px Roboto }",
        contentBefore: "<ol><li>[abc]</li><li>def</li></ol>",
        stepFunction: setFontSize("56px"),
        contentAfter: `<ol style="padding-inline-start: 60px;"><li style="font-size: 56px;">[abc]</li><li>def</li></ol>`,
    });
});

test.tags("font-dependent");
test("should apply font-size to completely selected list item (2)", async () => {
    await testEditor({
        styleContent: ":root { font: 14px Roboto }",
        contentBefore: unformat(`
            <ol>
                <li><p>[abc</p>
                    <ol>
                        <li>def</li>
                    </ol>
                </li>
                <li>ghi]</li>
            </ol>
        `),
        stepFunction: setFontSize("64px"),
        contentAfter: unformat(`
            <ol style="padding-inline-start: 69px;">
                <li style="font-size: 64px;"><p>[abc</p>
                    <ol class="o_default_font_size" style="padding-inline-start: 68px;">
                        <li style="font-size: 64px;">def</li>
                    </ol>
                </li>
                <li style="font-size: 64px;">ghi]</li>
            </ol>
        `),
    });
});

test("should apply font-size to completely selected multiple list items", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def]</li></ul>",
        stepFunction: setFontSizeClassName("h2-fs"),
        contentAfter: '<ul><li class="h2-fs">[abc</li><li class="h2-fs">def]</li></ul>',
    });
});

test("should apply font size to a fully selected list item with trailing empty line (1)", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>]<br></li></ul>",
        stepFunction: setFontSize("56px"),
        contentAfter:
            '<ul style="padding-inline-start: 38px;"><li style="font-size: 56px;">[abc</li><li style="font-size: 56px;">]<br></li></ul>',
    });
});

test("should apply font size to a fully selected list item with trailing empty line (2)", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li><br>]<br></li></ul>",
        stepFunction: setFontSize("56px"),
        contentAfter:
            '<ul style="padding-inline-start: 38px;"><li style="font-size: 56px;">[abc</li><li style="font-size: 56px;"><br>]<br></li></ul>',
    });
});

test("should apply font size to a fully selected list item with trailing empty line (3)", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>abcd<br>]<br></li></ul>",
        stepFunction: setFontSize("56px"),
        contentAfter:
            '<ul style="padding-inline-start: 38px;"><li style="font-size: 56px;">[abc</li><li style="font-size: 56px;">abcd<br>]<br></li></ul>',
    });
});

test("should not apply font size to list item when selection excludes trailing empty line", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>abcd]<br><br></li></ul>",
        stepFunction: setFontSize("56px"),
        contentAfter:
            '<ul style="padding-inline-start: 38px;"><li style="font-size: 56px;">[abc</li><li><span style="font-size: 56px;">abcd]</span><br><br></li></ul>',
    });
});

test("should apply font-size on fully selected list items with empty text nodes at list boundaries", async () => {
    await testEditor({
        contentBefore: '<ul><li><a href="#">abc</a></li><li><a href="#">abc</a></li></ul>',
        contentBeforeEdit:
            '<ul><li>\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff</li><li>\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff</li></ul>',
        stepFunction: (editor) => {
            const listItems = editor.editable.querySelectorAll("li");
            // Set selection here because injected \ufeff can be excluded
            // from the DOM range.
            editor.shared.selection.setSelection({
                anchorNode: listItems[0].firstChild,
                anchorOffset: 0,
                focusNode: listItems[1].lastChild,
                focusOffset: nodeSize(listItems[1].lastChild),
            });
            // Empty text node at start of first <li>
            listItems[0].insertBefore(document.createTextNode(""), listItems[0].firstChild);
            // Empty text node at end of second <li>
            listItems[1].appendChild(document.createTextNode(""));
            setFontSize("32px")(editor);
        },
        contentAfterEdit:
            '<ul><li style="font-size: 32px;">\ufeff[<a href="#">\ufeffabc\ufeff</a>\ufeff</li><li style="font-size: 32px;">\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff]</li></ul>',
        contentAfter:
            '<ul><li style="font-size: 32px;">[<a href="#">abc</a></li><li style="font-size: 32px;"><a href="#">abc</a>]</li></ul>',
    });
});

test("should replace list item inline font-size with font-size class", async () => {
    await testEditor({
        contentBefore: '<ul><li style="font-size: 18px;">[abc]</li></ul>',
        stepFunction: setFontSizeClassName("h2-fs"),
        contentAfter: '<ul><li class="h2-fs">[abc]</li></ul>',
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
        stepFunction: setFontSizeClassName("h2-fs"),
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

test.tags("font-dependent");
test("should keep list item font-size on toggling list twice", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
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

test.tags("font-dependent");
test("should change font-size of a list item (2)", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
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
    await testEditor({
        contentBefore: "<ol><li>[a]</li></ol>",
        stepFunction: setFontSizeClassName("h2-fs"),
        contentAfter: `<ol><li class="h2-fs">[a]</li></ol>`,
    });
});

test.tags("font-dependent");
test("should pad list based on font-size (2)", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<span style="font-size: 56px">[a]</span>`,
        stepFunction: toggleOrderedList,
        contentAfter: `<ol style="padding-inline-start: 60px;"><li style="font-size: 56px;">[]a</li></ol>`,
    });
});

test.tags("font-dependent");
test("should apply color to a list containing sublist if list contents are fully selected", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: "<ol><li><p>[abc]</p><ol><li>def</li></ol></li></ol>",
        stepFunction: setFontSize("56px"),
        contentAfter: `<ol style="padding-inline-start: 60px;"><li style="font-size: 56px;"><p>[abc]</p><ol class="o_default_font_size"><li>def</li></ol></li></ol>`,
    });
});

test("should remove font-size from list item", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li style="font-size: 56px;">[a]</li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li>[a]</li></ol>`,
    });
});

test("should remove font-size class from list item", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li class="h2-fs">[a]</li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li>[a]</li></ol>`,
    });
});

test("should remove font-size from list item containing sublist", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li>a</li><li style="font-size: 56px;"><p>[b]</p><ol class="o_default_font_size"><li>c</li></ol></li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li>a</li><li><p>[b]</p><ol><li>c</li></ol></li></ol>`,
    });
});

test("should remove font-size class from list item containing sublist", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li>a</li><li class="h2-fs"><p>[b]</p><ol class="o_default_font_size"><li>c</li></ol></li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li>a</li><li><p>[b]</p><ol><li>c</li></ol></li></ol>`,
    });
});

test("should remove font-size and its classes from partially selected list item (1)", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li>a</li><li style="font-size: 56px;">b[c]d</li><li>e</li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li>a</li><li style="font-size: 56px;">b<span class="o_default_font_size">[c]</span>d</li><li>e</li></ol>`,
    });
});

test("should remove font-size and its classes from partially selected list item (2)", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li>a</li><li class="h2-fs">b[c]d</li><li>e</li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li>a</li><li class="h2-fs">b<span class="o_default_font_size">[c]</span>d</li><li>e</li></ol>`,
    });
});

test("should remove font-size and its classes from partially selected list item (3)", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li style="font-size: 56px;">a[bc</li><li style="font-size: 56px;">def</li><li style="font-size: 56px;">gh]i</li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol style="padding-inline-start: 60px;"><li style="font-size: 56px;">a<span class="o_default_font_size">[bc</span></li><li>def</li><li style="font-size: 56px;"><span class="o_default_font_size">gh]</span>i</li></ol>`,
    });
});

test("should remove font-size and its classes from partially selected list item (4)", async () => {
    await testEditor({
        styleContent: "ol { font: 14px Roboto }",
        contentBefore: `<ol><li class="h2-fs">a[bc</li><li class="h2-fs">def</li><li class="h2-fs">gh]i</li></ol>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<ol><li class="h2-fs">a<span class="o_default_font_size">[bc</span></li><li>def</li><li class="h2-fs"><span class="o_default_font_size">gh]</span>i</li></ol>`,
    });
});
