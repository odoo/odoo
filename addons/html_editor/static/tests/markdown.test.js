import { describe, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { testEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

describe("inline code", () => {
    test("should convert text into inline code (start) (1)", async () => {
        await testEditor({
            contentBefore: "<p>`ab[]cd</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>\u200B<code class="o_inline_code">ab</code>\u200B[]cd</p>',
        });
    });

    test("should convert text into inline code (start) (2)", async () => {
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>[]ab`cd</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>\u200B<code class="o_inline_code">[]ab</code>cd</p>',
        });
    });

    test("should convert text into inline code (middle) (1)", async () => {
        await testEditor({
            contentBefore: "<p>ab`cd[]ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">cd</code>\u200B[]ef</p>',
        });
    });

    test("should convert text into inline code (middle) (2)", async () => {
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>ab[]cd`ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code>ef</p>',
        });
    });

    test("should convert text into inline code (end) (1)", async () => {
        await testEditor({
            contentBefore: "<p>ab`cd[]</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">cd</code>\u200B[]</p>',
        });
    });

    test("should convert text into inline code (end) (2)", async () => {
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>ab[]cd`</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code></p>',
        });
    });

    test("should convert text into inline code, with parasite backticks (1)", async () => {
        await testEditor({
            contentBefore: "<p>a`b`cd[]e`f</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            // The closest PREVIOUS backtick is prioritary
            contentAfter: '<p>a`b<code class="o_inline_code">cd</code>\u200B[]e`f</p>',
        });
    });

    test("should convert text into inline code, with parasite backticks (2)", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd`e`f</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            // If there is no previous backtick, use the closest NEXT backtick.
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
            contentAfter: '<p>ab<code class="o_inline_code">c</code>\u200B[]d</p>',
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
            contentAfter: '<p>a<code class="o_inline_code">b</code>\u200B[]cd</p>',
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
            contentAfter: '<p>ab<code class="o_inline_code">c</code>\u200B[]de</p>',
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
            contentAfter: '<p>\u200B<code class="o_inline_code">ab</code>\u200B[]c</p>',
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
});
