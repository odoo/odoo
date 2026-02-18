import { testEditor } from "../_helpers/editor";
import { test } from "@odoo/hoot";
import {
    setFontSize,
    splitBlock,
    toggleOrderedList,
    toggleUnorderedList,
} from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";
import { nodeSize } from "@html_editor/utils/position";

test("should apply font-size to completely selected list item", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc]</li><li>def</li></ol>",
        stepFunction: setFontSize("56px"),
        contentAfter:
            '<ol><li style="font-size: 56px; list-style-position: inside;">[abc]</li><li>def</li></ol>',
    });
});

test("should apply font-size to completely selected multiple list items", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def]</li></ul>",
        stepFunction: (editor) =>
            execCommand(editor, "formatFontSizeClassName", { className: "h2-fs" }),
        contentAfter:
            '<ul><li class="h2-fs" style="list-style-position: inside;">[abc</li><li class="h2-fs" style="list-style-position: inside;">def]</li></ul>',
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
            '<ul><li style="font-size: 32px; list-style-position: inside;">[\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff</li><li style="font-size: 32px; list-style-position: inside;">\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff]</li></ul>',
        contentAfter:
            '<ul><li style="font-size: 32px; list-style-position: inside;">[<a href="#">abc</a></li><li style="font-size: 32px; list-style-position: inside;"><a href="#">abc</a>]</li></ul>',
    });
});

test("should replace list item inline font-size with font-size class", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="font-size: 18px; list-style-position: inside;">[abc]</li></ul>',
        stepFunction: (editor) =>
            execCommand(editor, "formatFontSizeClassName", { className: "h2-fs" }),
        contentAfter: '<ul><li style="list-style-position: inside;" class="h2-fs">[abc]</li></ul>',
    });
});

test("should apply font-size to completely selected and partially selected list items", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc</li><li>def</li><li>gh]i</li></ol>",
        stepFunction: setFontSize("18px"),
        contentAfter:
            '<ol><li style="font-size: 18px; list-style-position: inside;">[abc</li><li style="font-size: 18px; list-style-position: inside;">def</li><li><span style="font-size: 18px;">gh]</span>i</li></ol>',
    });
});

test("should apply font-size to completely selected list items and paragraph tag", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def</li></ul><p>ghi]</p>",
        stepFunction: (editor) =>
            execCommand(editor, "formatFontSizeClassName", { className: "display-3-fs" }),
        contentAfter:
            '<ul><li class="display-3-fs" style="list-style-position: inside;">[abc</li><li class="display-3-fs" style="list-style-position: inside;">def</li></ul><p><span class="display-3-fs">ghi]</span></p>',
    });
});

test("should carry list item font-size to new list item", async () => {
    await testEditor({
        contentBefore:
            '<ol><li>abc</li><li style="font-size: 18px; list-style-position: inside;">def[]</li></ol>',
        stepFunction: splitBlock,
        contentAfter:
            '<ol><li>abc</li><li style="font-size: 18px; list-style-position: inside;">def</li><li style="font-size: 18px; list-style-position: inside;">[]<br></li></ol>',
    });
});

test("should carry list item font-size to new list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ul><li class="display-3-fs" style="list-style-position: inside;">[]abc</li><li>def</li></ul>',
        stepFunction: splitBlock,
        contentAfter:
            '<ul><li class="display-3-fs" style="list-style-position: inside;"><br></li><li class="display-3-fs" style="list-style-position: inside;">[]abc</li><li>def</li></ul>',
    });
});

test("should carry font-size of paragraph to list item", async () => {
    await testEditor({
        contentBefore:
            '<p><span style="font-size: 18px; list-style-position: inside;">[]abc</span></p>',
        stepFunction: toggleUnorderedList,
        contentAfter:
            '<ul><li style="font-size: 18px; list-style-position: inside;">[]abc</li></ul>',
    });
});

test("should carry font-size of paragraph to list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li class="h3-fs" style="list-style-position: inside;">abc</li></ol><p><span class="display-3-fs" style="list-style-position: inside;">[]def</span></p><ol><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li class="h3-fs" style="list-style-position: inside;">abc</li><li class="display-3-fs" style="list-style-position: inside;">[]def</li><li>ghi</li></ol>',
    });
});

test("should carry font-size of paragraph to list item (3)", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="font-size: 18px; list-style-position: inside;">abc</li></ul><p>[]def</p><ul><li style="font-size: 18px; list-style-position: inside;">ghi</li></ul>',
        stepFunction: toggleUnorderedList,
        contentAfter:
            '<ul><li style="font-size: 18px; list-style-position: inside;">abc</li><li>[]def</li><li style="font-size: 18px; list-style-position: inside;">ghi</li></ul>',
    });
});

test("should carry font-size of list item to paragraph", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">[]abc</li><li>def</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter: '<p><span style="font-size: 18px;">[]abc</span></p><ol><li>def</li></ol>',
    });
});

test("should carry font-size of list item to paragraph (2)", async () => {
    await testEditor({
        contentBefore:
            '<ul><li class="display-3-fs" style="list-style-position: inside;">abc</li><li class="display-3-fs" style="list-style-position: inside;">[]def</li><li>ghi</li></ul>',
        stepFunction: toggleUnorderedList,
        contentAfter:
            '<ul><li class="display-3-fs" style="list-style-position: inside;">abc</li></ul><p><span class="display-3-fs">[]def</span></p><ul><li>ghi</li></ul>',
    });
});

test("should carry font-size of list item to paragraph (3)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">abc</li><li>[]def</li><li>ghi</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<ol><li style="font-size: 18px; list-style-position: inside;">abc</li></ol><p>[]def</p><ol><li>ghi</li></ol>',
    });
});

test("should carry font-size of list item to paragraph (4)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">abc<span style="font-size: 32px;">def</span>ghi[]</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<p><span style="font-size: 18px;">abc<span style="font-size: 32px;">def</span>ghi[]</span></p>',
    });
});

test("should keep list item font-size on toggling list twice", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">[abc</li><li style="font-size: 32px; list-style-position: inside;">def]</li></ol>',
        stepFunction: (editor) => {
            toggleOrderedList(editor);
            toggleOrderedList(editor);
        },
        contentAfter:
            '<ol><li style="font-size: 18px; list-style-position: inside;">[abc</li><li style="font-size: 32px; list-style-position: inside;">def]</li></ol>',
    });
});

test("should change font-size of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="font-size: 18px; list-style-position: inside;">[abc]</li><li style="font-size: 18px; list-style-position: inside;">ghi</li></ul>',
        stepFunction: setFontSize("32px"),
        contentAfter:
            '<ul><li style="list-style-position: inside; font-size: 32px;">[abc]</li><li style="font-size: 18px; list-style-position: inside;">ghi</li></ul>',
    });
});

test("should change font-size of a list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">[abc</li><li style="font-size: 18px; list-style-position: inside;">ghi]</li></ol>',
        stepFunction: setFontSize("32px"),
        contentAfter:
            '<ol><li style="list-style-position: inside; font-size: 32px;">[abc</li><li style="list-style-position: inside; font-size: 32px;">ghi]</li></ol>',
    });
});

test("should change font-size of subpart of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">a[b]c</li><li style="font-size: 18px; list-style-position: inside;">ghi</li></ol>',
        stepFunction: setFontSize("32px"),
        contentAfter:
            '<ol><li style="font-size: 18px; list-style-position: inside;">a<span style="font-size: 32px;">[b]</span>c</li><li style="font-size: 18px; list-style-position: inside;">ghi</li></ol>',
    });
});

test("should change font-size of subpart of a list item (2)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="font-size: 18px; list-style-position: inside;">a[bc</li><li style="font-size: 18px; list-style-position: inside;">gh]i</li></ol>',
        stepFunction: setFontSize("32px"),
        contentAfter:
            '<ol><li style="font-size: 18px; list-style-position: inside;">a<span style="font-size: 32px;">[bc</span></li><li style="font-size: 18px; list-style-position: inside;"><span style="font-size: 32px;">gh]</span>i</li></ol>',
    });
});

test("should remove font-size style on converting the text to a block tag", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="font-size: 32px; list-style-position: inside;">a[]bc</li></ul>',
        stepFunction: (editor) => editor.shared.dom.setTag({ tagName: "H1" }),
        contentAfter: '<ul><li><h1><span style="font-size: 32px;">a[]bc</span></h1></li></ul>',
    });
});

test("should remove font-size class on converting the text to a block tag", async () => {
    await testEditor({
        contentBefore:
            '<ul><li class="display-3-fs" style="list-style-position: inside;">a[]bc</li></ul>',
        stepFunction: (editor) => editor.shared.dom.setTag({ tagName: "H1" }),
        contentAfter: '<ul><li><h1><span class="display-3-fs">a[]bc</span></h1></li></ul>',
    });
});
