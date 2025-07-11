import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { click, waitFor } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";
import { cleanLinkArtifacts } from "../_helpers/format";
import { contains } from "@web/../tests/_framework/dom_test_helpers";

test("should parse correctly a span inside a Link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"><span class="a">b[]</span></a>c</p>',
        contentAfter: '<p>a<a href="http://test.test/"><span class="a">b[]</span></a>c</p>',
    });
});

test("should parse correctly an empty span inside a Link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]<span class="a"></span></a>c</p>',
        contentAfter: '<p>a<a href="http://test.test/">b[]<span class="a"></span></a>c</p>',
    });
});

test("should parse correctly a span inside a Link 2", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"><span class="a">b[]</span>c</a>d</p>',
        contentAfter: '<p>a<a href="http://test.test/"><span class="a">b[]</span>c</a>d</p>',
    });
});

test("should parse correctly an empty span inside a Link then add a char", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]<span class="a"></span></a>c</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="http://test.test/">bc[]<span class="a"></span></a>c</p>',
    });
});

test("should parse correctly a span inside a Link then add a char", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"><span class="a">b[]</span></a>d</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
        },
        // JW cAfter: '<p>a<span><a href="http://test.test/">b</a>c[]</span>d</p>',
        contentAfter: '<p>a<a href="http://test.test/"><span class="a">bc[]</span></a>d</p>',
    });
});

test("should parse correctly a span inside a Link then add a char 2", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"><span class="a">b[]</span>d</a>e</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="http://test.test/"><span class="a">bc[]</span>d</a>e</p>',
    });
});

test("should parse correctly a span inside a Link then add a char 3", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"><span class="a">b</span>c[]</a>e</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "d");
        },
        // JW cAfter: '<p>a<a href="http://test.test/"><span class="a">b</span>c</a>d[]e</p>',
        contentAfter: '<p>a<a href="http://test.test/"><span class="a">b</span>cd[]</a>e</p>',
    });
});

test("should add a character after the link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]</a>d</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
        },
        // JW cAfter: '<p>a<a href="http://test.test/">b</a>c[]d</p>',
        contentAfter: '<p>a<a href="http://test.test/">bc[]</a>d</p>',
    });
});

test("should add two character after the link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]</a>e</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "cd");
        },
        contentAfter: '<p>a<a href="http://test.test/">bcd[]</a>e</p>',
    });
});

test("should add a character after the link if range just after link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b</a>[]d</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="exist">b</a>c[]d</p>',
    });
});

test("should add a character in the link after a br tag", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b<br>[]</a>d</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="http://test.test/">b<br>c[]</a>d</p>',
    });
});

test("should remove an empty link on save", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]</a>c</p>',
        contentBeforeEdit:
            '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffb[]\ufeff</a>\ufeffc</p>',
        stepFunction: deleteBackward,
        contentAfterEdit:
            '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]\ufeff</a>\ufeffc</p>',
        contentAfter: "<p>a[]c</p>",
    });
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"></a>b</p>',
        contentBeforeEdit: '<p>a\ufeff<a href="http://test.test/">\ufeff\ufeff</a>\ufeffb</p>',
        contentAfterEdit: '<p>a\ufeff<a href="http://test.test/">\ufeff\ufeff</a>\ufeffb</p>',
        contentAfter: "<p>ab</p>",
    });
});

test("should not remove a link containing an image on save", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><img></a>b</p>',
        contentBeforeEdit: '<p>a<a href="exist"><img></a>b</p>',
        contentAfterEdit: '<p>a<a href="exist"><img></a>b</p>',
        contentAfter: '<p>a<a href="exist"><img></a>b</p>',
    });
});

test("should not remove a document link on save", async () => {
    await testEditor({
        contentBefore:
            '<p>a<a href="exist" class="o_image" title="file.js.map" data-mimetype="text/plain"></a>b</p>',
        contentBeforeEdit:
            '<p>a<a href="exist" class="o_image" title="file.js.map" data-mimetype="text/plain" contenteditable="false"></a>b</p>',
        contentAfterEdit:
            '<p>a<a href="exist" class="o_image" title="file.js.map" data-mimetype="text/plain" contenteditable="false"></a>b</p>',
        contentAfter:
            '<p>a<a href="exist" class="o_image" title="file.js.map" data-mimetype="text/plain"></a>b</p>',
    });
});

test("should not remove a link containing a pictogram on save", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist"><span class="fa fa-star"></span></a>b</p>',
        contentBeforeEdit:
            '<p>a\ufeff<a href="exist">\ufeff<span class="fa fa-star" contenteditable="false">\u200b</span>\ufeff</a>\ufeffb</p>',
        contentAfterEdit:
            '<p>a\ufeff<a href="exist">\ufeff<span class="fa fa-star" contenteditable="false">\u200b</span>\ufeff</a>\ufeffb</p>',
        contentAfter: '<p>a<a href="exist"><span class="fa fa-star"></span></a>b</p>',
    });
});

test("should not add a character in the link if start of paragraph", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="exist">b</a></p><p>[]d</p>',
        stepFunction: async (editor) => {
            await insertText(editor, "c");
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
test("should not allow to extend a link if selection spans multiple links", async () => {
    const { el } = await setupEditor(
        '<p>xxx <a href="exist">lin[k1</a> yyy <a href="exist">li]nk2</a> zzz</p>'
    );
    await waitFor(".o-we-toolbar");
    // link button should be disabled
    expect('.o-we-toolbar button[name="link"]').toHaveClass("disabled");
    expect('.o-we-toolbar button[name="link"]').toHaveAttribute("disabled");
    await click('.o-we-toolbar button[name="link"]');
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>xxx <a href="exist">lin[k1</a> yyy <a href="exist">li]nk2</a> zzz</p>'
    );
});
test("should not allow to extend a link if selection spans multiple links (2)", async () => {
    const { el } = await setupEditor(
        '<p>xxx <a href="exist">[link1</a> yyy <a href="exist">li]nk2</a> zzz</p>'
    );
    await waitFor(".o-we-toolbar");
    // link button should be disabled
    expect('.o-we-toolbar button[name="link"]').toHaveClass("disabled");
    expect('.o-we-toolbar button[name="link"]').toHaveAttribute("disabled");
    await click('.o-we-toolbar button[name="link"]');
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>xxx <a href="exist">[link1</a> yyy <a href="exist">li]nk2</a> zzz</p>'
    );
});
test("should not allow to extend a link if selection spans multiple links (3)", async () => {
    const { el } = await setupEditor(
        '<p>xxx <a href="exist">[link1</a> yyy <a href="exist">link2]</a> zzz</p>'
    );
    await waitFor(".o-we-toolbar");
    // link button should be disabled
    expect('.o-we-toolbar button[name="link"]').toHaveClass("disabled");
    expect('.o-we-toolbar button[name="link"]').toHaveAttribute("disabled");
    await click('.o-we-toolbar button[name="link"]');
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>xxx <a href="exist">[link1</a> yyy <a href="exist">link2]</a> zzz</p>'
    );
});

test("when label === url popover label input should be empty", async () => {
    await setupEditor('<p>abc <a href="http://odoo.com">http://odo[]o.com</a> def</p>');
    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    await waitFor(".o_we_label_link");
    expect(".o_we_label_link").toHaveValue("");
});

test("when label === url changing url should change label", async () => {
    const { el } = await setupEditor(
        '<p>abc <a href="http://odoo.com">http://odo[]o.com</a> def</p>'
    );
    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    await waitFor(".o_we_label_link");
    expect(".o_we_label_link").toHaveValue("");

    await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.com");

    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>abc <a href="http://test.com">http://test.com[]</a> def</p>'
    );
});
