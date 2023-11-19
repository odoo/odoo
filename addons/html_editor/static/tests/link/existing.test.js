import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { insertText } from "../_helpers/user_actions";

test("should parse correctly a span inside a Link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><span class="a">b[]</span></a>c</p>',
        contentAfter: '<p>a<a href="exist"><span class="a">b[]</span></a>c</p>',
    });
});

test("should parse correctly an empty span inside a Link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b[]<span class="a"></span></a>c</p>',
        contentAfter: '<p>a<a href="exist">b[]<span class="a"></span></a>c</p>',
    });
});

test("should parse correctly a span inside a Link 2", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><span class="a">b[]</span>c</a>d</p>',
        contentAfter: '<p>a<a href="exist"><span class="a">b[]</span>c</a>d</p>',
    });
});

test("should parse correctly an empty span inside a Link then add a char", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b[]<span class="a"></span></a>c</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="exist">bc[]<span class="a"></span></a>c</p>',
    });
});

test("should parse correctly a span inside a Link then add a char", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><span class="a">b[]</span></a>d</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        // JW cAfter: '<p>a<span><a href="exist">b</a>c[]</span>d</p>',
        contentAfter: '<p>a<a href="exist"><span class="a">bc[]</span></a>d</p>',
    });
});

test("should parse correctly a span inside a Link then add a char 2", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><span class="a">b[]</span>d</a>e</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="exist"><span class="a">bc[]</span>d</a>e</p>',
    });
});

test("should parse correctly a span inside a Link then add a char 3", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><span class="a">b</span>c[]</a>e</p>',
        stepFunction: async (editor) => {
            insertText(editor, "d");
        },
        // JW cAfter: '<p>a<a href="exist"><span class="a">b</span>c</a>d[]e</p>',
        contentAfter: '<p>a<a href="exist"><span class="a">b</span>cd[]</a>e</p>',
    });
});

test("should add a character after the link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b[]</a>d</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        // JW cAfter: '<p>a<a href="exist">b</a>c[]d</p>',
        contentAfter: '<p>a<a href="exist">bc[]</a>d</p>',
    });
});

test("should add two character after the link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b[]</a>e</p>',
        stepFunction: async (editor) => {
            insertText(editor, "cd");
        },
        contentAfter: '<p>a<a href="exist">bcd[]</a>e</p>',
    });
});

test("should add a character after the link if range just after link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b</a>[]d</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="exist">b</a>c[]d</p>',
    });
});

test("should add a character in the link after a br tag", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b<br>[]</a>d</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="exist">b<br>c[]</a>d</p>',
    });
});

test("should not add a character in the link if start of paragraph", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b</a></p><p>[]d</p>',
        stepFunction: async (editor) => {
            insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="exist">b</a></p><p>c[]d</p>',
    });
});

// test.todo('should select and replace all text and add the next char in bold', async () => {
//     await testEditor({
//         contentBefore: '<div><p>[]123</p><p><a href="#">abc</a></p></div>',
//         stepFunction: async (editor) => {
//             const p = editor.selection.anchor.parent.nextSibling();
//             await editor.execCommand('setSelection', {
//                 vSelection: {
//                     anchorNode: p.firstLeaf(),
//                     anchorPosition: RelativePosition.BEFORE,
//                     focusNode: p.lastLeaf(),
//                     focusPosition: RelativePosition.AFTER,
//                     direction: Direction.FORWARD,
//                 },
//             });
//             await editor.execCommand('insert', 'd');
//         },
//         contentAfter: '<div><p>123</p><p><a href="#">d[]</a></p></div>',
//     });
// });
