import { describe, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { base64Img, testEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

describe("inline code", () => {
    test("should convert text into inline code (start) (1)", async () => {
        await testEditor({
            contentBefore: "<p>`ab[]cd</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>\ufeff<code class="o_inline_code">\ufeffab\ufeff</code>\ufeff[]cd</p>',
            contentAfter: '<p><code class="o_inline_code">ab</code>[]cd</p>',
        });
    });

    test("should convert text into inline code (start) (2)", async () => {
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>[]ab`cd</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>\ufeff<code class="o_inline_code">[]\ufeffab\ufeff</code>\ufeffcd</p>',
            contentAfter: '<p><code class="o_inline_code">[]ab</code>cd</p>',
        });
    });

    test("should convert text into inline code (middle) (1)", async () => {
        await testEditor({
            contentBefore: "<p>ab`cd[]ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffcd\ufeff</code>\ufeff[]ef</p>',
            contentAfter: '<p>ab<code class="o_inline_code">cd</code>[]ef</p>',
        });
    });

    test("should convert text into inline code (middle) (2)", async () => {
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>ab[]cd`ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">[]\ufeffcd\ufeff</code>\ufeffef</p>',
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code>ef</p>',
        });
    });

    test("should convert text into inline code (end) (1)", async () => {
        await testEditor({
            contentBefore: "<p>ab`cd[]</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffcd\ufeff</code>\ufeff[]</p>',
            contentAfter: '<p>ab<code class="o_inline_code">cd</code>[]</p>',
        });
    });

    test("should convert text into inline code (end) (2)", async () => {
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>ab[]cd`</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">[]\ufeffcd\ufeff</code>\ufeff</p>',
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code></p>',
        });
    });

    test("should convert text into inline code, with parasite backticks (1)", async () => {
        await testEditor({
            contentBefore: "<p>a`b`cd[]e`f</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            // The closest PREVIOUS backtick is prioritary
            contentAfterEdit:
                '<p>a`b\ufeff<code class="o_inline_code">\ufeffcd\ufeff</code>\ufeff[]e`f</p>',
            contentAfter: '<p>a`b<code class="o_inline_code">cd</code>[]e`f</p>',
        });
    });

    test("should convert text into inline code, with parasite backticks (2)", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd`e`f</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            // If there is no previous backtick, use the closest NEXT backtick.
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">[]\ufeffcd\ufeff</code>\ufeffe`f</p>',
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code>e`f</p>',
        });
    });

    test("should not convert text into inline code when traversing HTMLElements", async () => {
        await testEditor({
            contentBefore: "<p>ab`c<strong>d</strong>e[]fg</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: "<p>ab`c<strong>d</strong>e`[]fg</p>",
        });
    });

    test("should not convert text into inline code when interrupted by linebreak", async () => {
        await testEditor({
            contentBefore: "<p>ab`c<br>d[]ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: "<p>ab`c<br>d`[]ef</p>",
        });
    });

    test("should not convert text into inline code when inside inline code", async () => {
        await testEditor({
            contentBefore: '<p>a<code class="o_inline_code">b`cd[]e</code>f</p>',
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfterEdit:
                '<p>a\ufeff<code class="o_inline_code">\ufeffb`cd`[]e\ufeff</code>\ufefff</p>',
            contentAfter: '<p>a<code class="o_inline_code">b`cd`[]e</code>f</p>',
        });
    });

    test("should convert text into inline code even when text nodes are split (1)", async () => {
        // BEFORE
        await testEditor({
            contentBefore: "<p>b`c[]d</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.before(document.createTextNode("a"));

                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                await insertText(editor, "`");
            },
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffc\ufeff</code>\ufeff[]d</p>',
            contentAfter: '<p>ab<code class="o_inline_code">c</code>[]d</p>',
        });
    });

    test("should convert text into inline code even when text nodes are split (2)", async () => {
        // AFTER
        await testEditor({
            contentBefore: "<p>a`b[]c</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.after(document.createTextNode("d"));

                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                await insertText(editor, "`");
            },
            contentAfterEdit:
                '<p>a\ufeff<code class="o_inline_code">\ufeffb\ufeff</code>\ufeff[]cd</p>',
            contentAfter: '<p>a<code class="o_inline_code">b</code>[]cd</p>',
        });
    });

    test("should convert text into inline code even when text nodes are split (3)", async () => {
        // BOTH
        await testEditor({
            contentBefore: "<p>b`c[]d</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.before(document.createTextNode("a"));
                editor.document.getSelection().anchorNode.after(document.createTextNode("e"));

                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                await insertText(editor, "`");
            },
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffc\ufeff</code>\ufeff[]de</p>',
            contentAfter: '<p>ab<code class="o_inline_code">c</code>[]de</p>',
        });
    });

    test("should convert text into inline code even when the other backtick is in a separate text node (1)", async () => {
        // BACKTICK IS PREVIOUS SIBLING
        await testEditor({
            contentBefore: "<p>ab[]c</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.before(document.createTextNode("`"));

                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                await insertText(editor, "`");
            },
            contentAfterEdit:
                '<p>\ufeff<code class="o_inline_code">\ufeffab\ufeff</code>\ufeff[]c</p>',
            contentAfter: '<p><code class="o_inline_code">ab</code>[]c</p>',
        });
    });

    test("should convert text into inline code even when the other backtick is in a separate text node (2)", async () => {
        // BACKTICK IS NEXT SIBLING
        await testEditor({
            contentBefore: "<p>ab[]c</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.after(document.createTextNode("`"));

                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                await insertText(editor, "`");
            },
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">[]\ufeffc\ufeff</code>\ufeff</p>',
            contentAfter: '<p>ab<code class="o_inline_code">[]c</code></p>',
        });
    });

    test("should not convert text into inline code when content is empty (1)", async () => {
        await testEditor({
            contentBefore: "<p>`[]</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfter: "<p>``[]</p>",
        });
    });

    test("should not convert text into inline code when content is empty (2)", async () => {
        await testEditor({
            contentBefore: "<p>``[]</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfter: "<p>```[]</p>",
        });
    });

    test("should not convert text into inline code when content is empty (3)", async () => {
        await testEditor({
            contentBefore: "<p>```[]</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfter: "<p>````[]</p>",
        });
    });

    test("should not convert text into inline code when content is empty (4)", async () => {
        await testEditor({
            contentBefore: "<p>````[]</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfter: "<p>`````[]</p>",
        });
    });

    test("should wrap selection in inline code (1)", async () => {
        await testEditor({
            contentBefore: "<p>a[bc]d</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit:
                '<p>a\ufeff<code class="o_inline_code">\ufeffbc[]\ufeff</code>\ufeffd</p>',
            contentAfter: '<p>a<code class="o_inline_code">bc[]</code>d</p>',
        });
    });

    test("should wrap selection in inline code (2)", async () => {
        await testEditor({
            contentBefore: `<p>ab[cd<a href="#">test</a>ef]gh</p>`,
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit: `<p>ab\ufeff<code class="o_inline_code">\ufeffcd\ufeff<a href="#">\ufefftest\ufeff</a>\ufeffef[]\ufeff</code>\ufeffgh</p>`,
            contentAfter: `<p>ab<code class="o_inline_code">cd<a href="#">test</a>ef[]</code>gh</p>`,
        });
    });

    test("should split selected inline element and wrap only the selected text in inline code", async () => {
        await testEditor({
            contentBefore: "<p>ab[cd<strong>ef]g</strong>h</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffcd<strong>ef[]</strong>\ufeff</code>\ufeff<strong>g</strong>h</p>',
            contentAfter:
                '<p>ab<code class="o_inline_code">cd<strong>ef[]</strong></code><strong>g</strong>h</p>',
        });
    });

    test("should split selected inline element and wrap only the selected text in inline code(1)", async () => {
        await testEditor({
            contentBefore: "<p><strong>a<u>b[cd</u>ef]g</strong></p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit:
                '<p><strong>a<u>b</u></strong>\ufeff<code class="o_inline_code">\ufeff<strong><u>cd</u>ef[]</strong>\ufeff</code>\ufeff<strong>g</strong></p>',
            contentAfter:
                '<p><strong>a<u>b</u></strong><code class="o_inline_code"><strong><u>cd</u>ef[]</strong></code><strong>g</strong></p>',
        });
    });

    test("should apply inline code when selection partially includes a link", async () => {
        await testEditor({
            contentBefore: `<p>ab[cd<a href="#">te]st</a>ef</p>`,
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffcd\ufeff<a href="#" class="o_link_in_selection">\ufeffte[]\ufeff</a>\ufeff</code>\ufeff<a href="#">\ufeffst\ufeff</a>\ufeffef</p>',
            contentAfter:
                '<p>ab<code class="o_inline_code">cd<a href="#">te[]</a></code><a href="#">st</a>ef</p>',
        });
    });

    test("should wrap text selection in inline code but skip images (1)", async () => {
        await testEditor({
            contentBefore: `<p>a[bc<img src="${base64Img}">de]f</p>`,
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit: `<p>a\ufeff<code class="o_inline_code">\ufeffbc\ufeff</code>\ufeff<img src="${base64Img}">\ufeff<code class="o_inline_code">\ufeffde[]\ufeff</code>\ufefff</p>`,
            contentAfter: `<p>a<code class="o_inline_code">bc</code><img src="${base64Img}"><code class="o_inline_code">de[]</code>f</p>`,
        });
    });

    test("should wrap text selection in inline code but skip images (2)", async () => {
        await testEditor({
            contentBefore: `<p>a[bcde<img src="${base64Img}">]</p>`,
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit: `<p>a\ufeff<code class="o_inline_code">\ufeffbcde[]\ufeff</code>\ufeff<img src="${base64Img}"></p>`,
            contentAfter: `<p>a<code class="o_inline_code">bcde[]</code><img src="${base64Img}"></p>`,
        });
    });

    test("should convert partially selected button into link and wrap selection in inline code", async () => {
        await testEditor({
            contentBefore: `<p>ab[cd<a href="#" class="btn btn-primary">te]st</a>ef</p>`,
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit:
                '<p>ab\ufeff<code class="o_inline_code">\ufeffcd\ufeff<a href="#" class="o_link_in_selection">\ufeffte[]\ufeff</a>\ufeff</code>\ufeff<a href="#" class="btn btn-primary">\ufeffst\ufeff</a>\ufeffef</p>',
            contentAfter:
                '<p>ab<code class="o_inline_code">cd<a href="#">te[]</a></code><a href="#" class="btn btn-primary">st</a>ef</p>',
        });
    });

    test("should not create an empty inline code when there is no text between two backticks", async () => {
        await testEditor({
            contentBefore: "<p>a`[]b</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit: "<p>a``[]b</p>",
            contentAfter: "<p>a``[]b</p>",
        });
    });

    test("should not create an empty inline code when there is a backtick between two backticks", async () => {
        await testEditor({
            contentBefore: "<p>a``[]b</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfterEdit: "<p>a```[]b</p>",
            contentAfter: "<p>a```[]b</p>",
        });
    });

    test("should not apply inline code when selection spans multiple block elements", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>cd</p><p>e]f</p>",
            stepFunction: async (editor) => insertText(editor, "`"),
            contentAfter: "<p>a`[]f</p>",
        });
    });
});
