import { testEditor } from "../_helpers/editor";
import { test } from "@odoo/hoot";
import {
    setColor,
    splitBlock,
    toggleOrderedList,
    toggleUnorderedList,
} from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";
import { unformat } from "../_helpers/format";
import { nodeSize } from "@html_editor/utils/position";

test("should apply color to completely selected list item", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc]</li><li>def</li></ol>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: '<ol><li style="color: rgb(255, 0, 0);">[abc]</li><li>def</li></ol>',
    });
});

test("should apply color to completely selected multiple list items", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def]</li></ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">def]</li></ul>',
    });
});

test("should color a fully selected list item with trailing empty line (1)", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>]<br></li></ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">]<br></li></ul>',
    });
});

test("should color a fully selected list item with trailing empty line (2)", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li><br>]<br></li></ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);"><br>]<br></li></ul>',
    });
});

test("should color a fully selected list item with trailing empty line (3)", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>abcd<br>]<br></li></ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">abcd<br>]<br></li></ul>',
    });
});

test("should color a fully selected list item with trailing empty line (4)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ol>
                <li>
                    <p>[abc</p>
                    <ol>
                        <li>]<br></li>
                    </ol>
                </li>
            </ol>
        `),
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: unformat(`
            <ol>
                <li style="color: rgb(255, 0, 0);">
                    <p>[abc</p>
                    <ol>
                        <li style="color: rgb(255, 0, 0);">]<br></li>
                    </ol>
                </li>
            </ol>
        `),
    });
});

test("should not color list item when selection excludes trailing empty line", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>abcd]<br><br></li></ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[abc</li><li><font style="color: rgb(255, 0, 0);">abcd]</font><br><br></li></ul>',
    });
});

test("should apply color on fully selected list items with empty text nodes at list boundaries", async () => {
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
            setColor("rgb(255, 0, 0)", "color")(editor);
        },
        contentAfterEdit:
            '<ul><li style="color: rgb(255, 0, 0);">[\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff</li><li style="color: rgb(255, 0, 0);">\ufeff<a href="#">\ufeffabc\ufeff</a>\ufeff]</li></ul>',
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[<a href="#">abc</a></li><li style="color: rgb(255, 0, 0);"><a href="#">abc</a>]</li></ul>',
    });
});

test("should apply color to completely selected and partially selected list items", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc</li><li>def</li><li>gh]i</li></ol>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">def</li><li><font style="color: rgb(255, 0, 0);">gh]</font>i</li></ol>',
    });
});

test("should apply color to completely selected list items and paragraph tag", async () => {
    await testEditor({
        contentBefore: "<ul><li>[abc</li><li>def</li></ul><p>ghi]</p>",
        stepFunction: setColor("rgb(255, 0, 0", "color"),
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">[abc</li><li style="color: rgb(255, 0, 0);">def</li></ul><p><font style="color: rgb(255, 0, 0);">ghi]</font></p>',
    });
});

test("should carry list item color to new list item", async () => {
    await testEditor({
        contentBefore: '<ol><li>abc</li><li style="color: rgb(255, 0, 0);">def[]</li></ol>',
        stepFunction: splitBlock,
        contentAfter:
            '<ol><li>abc</li><li style="color: rgb(255, 0, 0);">def</li><li style="color: rgb(255, 0, 0);">[]<br></li></ol>',
    });
});

test("should carry list item color to new list item (2)", async () => {
    await testEditor({
        contentBefore: '<ul><li style="color: rgb(255, 0, 0);">[]abc</li><li>def</li></ul>',
        stepFunction: splitBlock,
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);"><br></li><li style="color: rgb(255, 0, 0);">[]abc</li><li>def</li></ul>',
    });
});

test("should carry color of paragraph to list item", async () => {
    await testEditor({
        contentBefore: '<p><font style="color: rgb(255, 0, 0);">[]abc</font></p>',
        stepFunction: toggleUnorderedList,
        contentAfter: '<ul><li style="color: rgb(255, 0, 0);">[]abc</li></ul>',
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

test("should carry color of paragraph to list item (3)", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="color: rgb(255, 0, 0);">abc</li></ul><p>[]def</p><ul><li style="color: rgb(255, 0, 0);">ghi</li></ul>',
        stepFunction: toggleUnorderedList,
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">abc</li><li>[]def</li><li style="color: rgb(255, 0, 0);">ghi</li></ul>',
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
            '<ul><li style="color: rgb(255, 0, 0);">abc</li><li style="color: rgb(0, 0, 255);">[]def</li><li>ghi</li></ul>',
        stepFunction: toggleUnorderedList,
        contentAfter:
            '<ul><li style="color: rgb(255, 0, 0);">abc</li></ul><p><font style="color: rgb(0, 0, 255);">[]def</font></p><ul><li>ghi</li></ul>',
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

test("should carry color of list item to paragraph (4)", async () => {
    await testEditor({
        contentBefore:
            '<ol><li style="color: rgb(255, 0, 0);">abc<font style="color: rgb(0, 255, 0)">def</font>ghi[]</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter:
            '<p><font style="color: rgb(255, 0, 0);">abc<font style="color: rgb(0, 255, 0)">def</font>ghi[]</font></p>',
    });
});

test("should carry class-defined color of list item to paragraph", async () => {
    await testEditor({
        contentBefore: '<ol><li class="text-o-color-1">[]abc</li><li>def</li></ol>',
        stepFunction: toggleOrderedList,
        contentAfter: '<p><font class="text-o-color-1">[]abc</font></p><ol><li>def</li></ol>',
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
    await testEditor({
        contentBefore:
            '<ul><li style="color: rgb(255, 0, 0);">abc</li><li style="color: rgb(255, 0, 0);">[ghi]</li></ul>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: '<ul><li style="color: rgb(255, 0, 0);">abc</li><li>[ghi]</li></ul>',
    });
});

test("should remove color from partially selected list item", async () => {
    await testEditor({
        contentBefore: '<ol><li style="color: rgb(255, 0, 0);">ab[cd]ef</li></ol>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<ol><li style="color: rgb(255, 0, 0);">ab<font style="color: initial;">[cd]</font>ef</li></ol>',
    });
});

test("should change color of a list item", async () => {
    await testEditor({
        contentBefore:
            '<ul><li style="color: rgb(255, 0, 0);">[abc]</li><li style="color: rgb(255, 0, 0);">ghi</li></ul>',
        stepFunction: setColor("rgb(0, 0, 255)", "color"),
        contentAfter:
            '<ul><li style="color: rgb(0, 0, 255);">[abc]</li><li style="color: rgb(255, 0, 0);">ghi</li></ul>',
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

test("should apply gradient color style only on font inside list item", async () => {
    await testEditor({
        contentBefore: "<ol><li>[abc]</li><li>def</li></ol>",
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%)",
            "color"
        ),
        contentAfter:
            '<ol><li><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%);">[abc]</font></li><li>def</li></ol>',
    });
});
