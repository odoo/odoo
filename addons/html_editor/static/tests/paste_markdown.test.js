import { MarkdownPlugin } from "@html_editor/main/markdown/markdown_plugin";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { press, queryAllTexts, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { onRpc } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import { insertText, pasteText } from "./_helpers/user_actions";

beforeEach(() => {
    onRpc("/html_editor/markdown_to_html", () => false);
});

describe("powerbox", () => {
    test("should open the powerbox when pasting Markdown", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold**");
        await expectElementCount(".o-we-powerbox", 1);
        expect(queryAllTexts(".o-we-powerbox .o-we-command-name")).toEqual([
            "Convert Markdown",
            "Paste as plain text",
        ]);
        // The Markdown is pasted as text while the user makes a choice.
        expect(getContent(el)).toBe("<p>ab**bold**[]cd</p>");
    });

    test("should not open the powerbox when pasting regular text", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "Hello world, 2 * 3 = 6 and my_variable_name.");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);
        expect(getContent(el)).toBe("<p>abHello world, 2 * 3 = 6 and my_variable_name.[]cd</p>");
    });

    test("should not open the powerbox when the plugin is not loaded", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        pasteText(editor, "**bold**");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);
        expect(getContent(el)).toBe("<p>ab**bold**[]cd</p>");
    });

    test("should convert Markdown when applying the first command", async () => {
        onRpc("/html_editor/markdown_to_html", async (request) => {
            const { params } = await request.json();
            expect.step(params.text);
            return "<p><strong>bold</strong> text</p>";
        });
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold** text");
        await expectElementCount(".o-we-powerbox", 1);
        await press("Enter");
        await animationFrame();
        expect.verifySteps(["**bold** text"]);
        expect(getContent(el)).toBe("<p>ab<strong>bold</strong> text[]cd</p>");
    });

    test("should sanitize the converted HTML", async () => {
        onRpc(
            "/html_editor/markdown_to_html",
            () => '<p><strong onclick="alert(1)">bold</strong> text</p>'
        );
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold** text");
        await expectElementCount(".o-we-powerbox", 1);
        await press("Enter");
        await animationFrame();
        expect(getContent(el)).toBe("<p>ab<strong>bold</strong> text[]cd</p>");
    });

    test("should paste Markdown as text when applying the second command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold** text");
        await expectElementCount(".o-we-powerbox", 1);
        await press("ArrowDown");
        await press("Enter");
        await waitForNone(".o-we-powerbox");
        expect(getContent(el)).toBe("<p>ab**bold** text[]cd</p>");
    });

    test("should keep Markdown as text when closing the powerbox", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: async (editor) => {
                pasteText(editor, "**bold** text");
                await expectElementCount(".o-we-powerbox", 1);
                await press("Escape");
                await waitForNone(".o-we-powerbox");
            },
            contentAfter: "<p>ab**bold** text[]cd</p>",
            config: { includePlugins: [MarkdownPlugin] },
        });
    });

    test("should keep Markdown as text when the conversion fails", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold** text");
        await expectElementCount(".o-we-powerbox", 1);
        await press("Enter");
        await animationFrame();
        expect(getContent(el)).toBe("<p>ab**bold** text[]cd</p>");
    });

    test("should not convert Markdown when the content changed during the conversion", async () => {
        const { promise, resolve } = Promise.withResolvers();
        onRpc("/html_editor/markdown_to_html", () => promise);
        const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold**");
        await expectElementCount(".o-we-powerbox", 1);
        await press("Enter");
        await animationFrame();
        await insertText(editor, "x");
        resolve("<p><strong>bold</strong></p>");
        await animationFrame();
        expect(getContent(el)).toBe("<p>ab**bold**x[]cd</p>");
    });

    test("should still convert URLs to links when pasting Markdown as text", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "[Odoo](https://www.odoo.com) website");
        await expectElementCount(".o-we-powerbox", 1);
        await press("ArrowDown");
        await press("Enter");
        expect(getContent(el)).toBe(
            `<p>[Odoo](\ufeff<a href="https://www.odoo.com">\ufeffhttps://www.odoo.com\ufeff</a>\ufeff) website[]</p>`
        );
    });

    test("should not open the powerbox when pasting Markdown in a code block", async () => {
        const { el, editor } = await setupEditor("<pre>[]<br></pre>", {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "# Title");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);
        expect(getContent(el)).toBe("<pre># Title[]</pre>");
    });

    test("should not open the powerbox when pasting Markdown in inline code", async () => {
        const { el, editor } = await setupEditor('<p><code class="o_inline_code">a[]b</code></p>', {
            config: { includePlugins: [MarkdownPlugin] },
        });
        pasteText(editor, "**bold**");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(0);
        expect(getContent(el)).toBe(
            `<p>\ufeff<code class="o_inline_code">\ufeffa**bold**[]b\ufeff</code>\ufeff</p>`
        );
    });
});
