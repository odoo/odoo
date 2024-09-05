import { describe, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { testEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

describe("inline code", () => {
    test("should convert text into inline code (start)", async () => {
        await testEditor({
            contentBefore: "<p>`ab[]cd</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>\u200B<code class="o_inline_code">ab</code>\u200B[]cd</p>',
        });
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>[]ab`cd</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>\u200B<code class="o_inline_code">[]ab</code>cd</p>',
        });
    });

    test("should convert text into inline code (middle)", async () => {
        await testEditor({
            contentBefore: "<p>ab`cd[]ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">cd</code>\u200B[]ef</p>',
        });
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>ab[]cd`ef</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code>ef</p>',
        });
    });

    test("should convert text into inline code (end)", async () => {
        await testEditor({
            contentBefore: "<p>ab`cd[]</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">cd</code>\u200B[]</p>',
        });
        // BACKWARDS
        await testEditor({
            contentBefore: "<p>ab[]cd`</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            contentAfter: '<p>ab<code class="o_inline_code">[]cd</code></p>',
        });
    });

    test("should convert text into inline code, with parasite backticks", async () => {
        await testEditor({
            contentBefore: "<p>a`b`cd[]e`f</p>",
            stepFunction: async (editor) => await insertText(editor, "`"),
            // The closest PREVIOUS backtick is prioritary
            contentAfter: '<p>a`b<code class="o_inline_code">cd</code>\u200B[]e`f</p>',
        });
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

    test("should convert text into inline code even when text nodes are split", async () => {
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
        // AFTER
        await testEditor({
            contentBefore: "<p>a`b[]c</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.after(document.createTextNode("d"));
                await insertText(editor, "`");
            },
            contentAfter: '<p>a<code class="o_inline_code">b</code>\u200B[]cd</p>',
        });
        // BOTH
        await testEditor({
            contentBefore: "<p>b`c[]d</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.before(document.createTextNode("a"));
                editor.document.getSelection().anchorNode.after(document.createTextNode("e"));
                await insertText(editor, "`");
            },
            contentAfter: '<p>ab<code class="o_inline_code">c</code>\u200B[]de</p>',
        });
    });

    test("should convert text into inline code even when the other backtick is in a separate text node", async () => {
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
        // BACKTICK IS NEXT SIBLING
        await testEditor({
            contentBefore: "<p>ab[]c</p>",
            stepFunction: async (editor) => {
                editor.document.getSelection().anchorNode.after(document.createTextNode("`"));
                await insertText(editor, "`");
            },
            contentAfter: '<p>ab<code class="o_inline_code">[]c</code></p>',
        });
    });
});
