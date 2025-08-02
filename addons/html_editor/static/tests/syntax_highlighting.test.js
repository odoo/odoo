import { beforeEach, expect, test } from "@odoo/hoot";
import { getContent } from "./_helpers/selection";
import { animationFrame, click, pointerUp, press, queryOne, waitFor } from "@odoo/hoot-dom";
import { insertText, splitBlock } from "./_helpers/user_actions";
import {
    compareHighlightedContent,
    patchPrism,
    testTextareaRange,
} from "./_helpers/syntax_highlighting";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { unformat } from "./_helpers/format";
import { setupEditor, testEditor } from "./_helpers/editor";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";

const insertPre = async (editor) => {
    await insertText(editor, "/code");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Code");
    await press("enter");
    await animationFrame();
};

const changeLanguage = async (textarea, from, to) => {
    await click(textarea);
    // Code Toolbar should open.
    await waitFor(`.o_code_toolbar button[name='language'][title='${from}']`);
    await click(`.o_code_toolbar button[name='language'][title='${from}']`);
    // Language selector dropdown should open.
    await waitFor(`.o_language_selector .o-dropdown-item[name='${to}']`);
    await click(`.o_language_selector .o-dropdown-item[name='${to}']`);
    // Code Toolbar should show the new language name.
    await waitFor(`.o_code_toolbar button[name='language'][title='${to}']`);
};

const configWithEmbeddings = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

beforeEach(patchPrism);

test("starting edition with a code block activates syntax highlighting", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>some code</pre>",
        contentBeforeEdit: { value: "some code" }, // TODO: should have focused the textarea.
        stepFunction: async () => press(["ctrl", "z"]),
        contentAfterEdit: { value: "some code" }, // Undo did nothing.
        config: configWithEmbeddings,
    });
});

test("starting edition with a syntax highlighting block with dataset values highlights the content", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: unformat(
            `<div data-embedded="syntaxHighlighting" data-oe-protected="true" contenteditable="false"
            class="o_syntax_highlighting" data-syntax-highlighting-value="Hello world!"
            data-language-id="javascript"></div>`
        ),
        // The DIV should now be filled with a highlighted pre and a textarea,
        // the respective values of which match the dataset.
        contentBeforeEdit: {
            value: "Hello world!",
            language: "javascript",
        },
        stepFunction: async (editor) => {
            await press(["ctrl", "z"]);
            await compareHighlightedContent(
                getContent(editor.editable),
                {
                    value: "Hello world!",
                    language: "javascript",
                },
                "Undo should have done nothing.",
                editor
            );
            await click("textarea");
            await press("a");
            await compareHighlightedContent(
                getContent(editor.editable),
                {
                    value: "Hello world!a",
                    language: "javascript",
                    textareaRange: 13, // "Hello world!a[]"
                },
                "Should have written at the end of the textarea.",
                editor
            );
            await press(["ctrl", "z"]);
            await press(["ctrl", "z"]);
        },
        contentAfterEdit: {
            value: "Hello world!",
            language: "javascript",
            textareaRange: 12, // "Hello world![]"
        }, // Undo did nothing.
        config: configWithEmbeddings,
    });
});

test("inserting a code block activates syntax highlighting plugin, typing triggers highlight", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<p>[]abc</p>",
        stepFunction: async (editor) => {
            await insertPre(editor);
            await compareHighlightedContent(
                getContent(editor.editable),
                {
                    value: "abc",
                    textareaRange: 3,
                },
                "The syntax highlighting wrapper was inserted, the paragraph's content is its value and the selection in at the end of the textarea.",
                editor
            );
            await press("d");
        },
        contentAfterEdit: {
            value: "abcd",
            textareaRange: 4,
        }, // The change of value in the textarea is reflected in the pre.
        config: configWithEmbeddings,
    });
});

test("inserting an empty code block activates syntax highlighting plugin with an empty textarea", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<p><br>[]</p>",
        stepFunction: insertPre,
        contentAfterEdit: {
            value: "",
            textareaRange: 0,
        },
        config: configWithEmbeddings,
    });
});

test("inserting a code block in an empty paragraph with a style placeholder activates syntax highlighting plugin with an empty textarea", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<p><br>[]</p>",
        stepFunction: async (editor) => {
            await press(["ctrl", "b"]);
            expect(getContent(editor.editable)).toBe(
                `<p o-we-hint-text='Type "/" for commands' class="o-we-hint"><strong data-oe-zws-empty-inline="">[]\u200B</strong></p>`,
                { message: "The style placeholder was inserted." }
            );
            splitBlock(editor);
            expect(getContent(editor.editable)).toBe(
                `<p><strong data-oe-zws-empty-inline="">\u200B</strong></p>` +
                    `<p o-we-hint-text='Type "/" for commands' class="o-we-hint"><strong data-oe-zws-empty-inline="">[]\u200B</strong></p>`,
                { message: "The paragraph was split." }
            );
            await insertPre(editor);
        },
        contentAfterEdit: [
            {
                value: `<p><strong data-oe-zws-empty-inline="">\u200B</strong></p>`,
                wrapped: false,
            },
            {
                value: "", // There should be no content (the zws is stripped)
                textareaRange: 0,
            },
        ],
        config: configWithEmbeddings,
    });
});

test.tags();
test("changing languages in a code block changes its highlighting", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>some code</pre>",
        contentBeforeEdit: { value: "some code" },
        stepFunction: async () => {
            await changeLanguage(queryOne("textarea"), "Plain Text", "Javascript");
        },
        contentAfterEdit: {
            value: "some code",
            language: "javascript",
            textareaRange: 9,
        },
        config: configWithEmbeddings,
    });
});

test("should fill an empty pre", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>abc</pre>",
        contentBeforeEdit: { value: "abc" },
        stepFunction: async () => {
            const textarea = queryOne("textarea");
            await click(textarea);
            textarea.select();
            await press("backspace");
        },
        contentAfterEdit: { value: "", textareaRange: 0 }, // Note: the BR is outside the highlight.
        config: configWithEmbeddings,
    });
});

test("the textarea should never contains zws", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>a\u200bb\ufeffc</pre>",
        contentBeforeEdit: { value: "abc" },
        stepFunction: async () => {
            const textarea = queryOne("textarea");
            await click(textarea);
        },
        contentAfterEdit: { value: "abc", textareaRange: 3 },
        config: configWithEmbeddings,
    });
});

test.tags();
test("can copy content with the copy button", async () => {
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>abc</pre>",
        contentBeforeEdit: { value: "abc" },
        stepFunction: async (editor) => {
            const textarea = queryOne("textarea");
            await click(textarea);
            testTextareaRange(editor, { el: textarea, value: "abc", range: 3 });
            await animationFrame();
            await waitFor(".o_code_toolbar");
            // Copy "abc".
            await click(".o_code_toolbar .o_clipboard_button");
            expect.verifySteps(["abc"]);
            // Change text.
            await click(textarea);
            testTextareaRange(editor, { el: textarea, value: "abc", range: 3 });
            await press("d");
            testTextareaRange(editor, { el: textarea, value: "abcd", range: 4 });
            // Copy "abcd"
            await click(".o_code_toolbar .o_clipboard_button");
            expect.verifySteps(["abcd"]);
            textarea.focus();
        },
        contentAfterEdit: {
            value: "abcd",
            textareaRange: 4,
        },
        config: configWithEmbeddings,
    });
});

test("tab in code block inserts 4 spaces", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>code</pre>",
        contentBeforeEdit: { value: "code" },
        stepFunction: async () => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(2, 2); // "co[]de"
            await press("tab");
        },
        contentAfterEdit: {
            value: `co    de`,
            textareaRange: 6, // "co    []de"
        },
        config: configWithEmbeddings,
    });
});

test("tab in selection in code block indents each selected line", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>a<br>b c<br> d</pre>",
        contentBeforeEdit: { value: "a\nb c\n d" },
        stepFunction: async (editor) => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(1, 7); // "a[\nb c\n ]d"
            await press("tab");
        },
        contentAfterEdit: {
            value: "    a\n    b c\n     d",
            textareaRange: [5, 19], // "    a[\n    b c\n     ]d"
        },
        config: configWithEmbeddings,
    });
});

test("shift+tab in code block outdents the current line", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>    some<br>       co    de<br>    for you</pre>",
        contentBeforeEdit: { value: "    some\n       co    de\n    for you" },
        stepFunction: async (editor) => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(22, 22); // "    some\n       co    []de\n    for you"
            await press(["shift", "tab"]);
            await compareHighlightedContent(
                getContent(editor.editable),
                [
                    {
                        value: `    some\n   co    de\n    for you`,
                        textareaRange: 18, // "    some\n   co    []de\n    for you"
                    },
                ],
                "The content was outdented a first time.",
                editor
            );
            await press(["shift", "tab"]);
        },
        contentAfterEdit: {
            value: `    some\nco    de\n    for you`,
            textareaRange: 15, // "    some\nco    []de\n    for you"
        },
        config: configWithEmbeddings,
    });
});

test("shift+tab in selection in code block outdents each selected line", async () => {
    await testEditor({
        compareFunction: compareHighlightedContent,
        contentBefore: "<pre>    a<br>    b c<br>     d</pre>",
        contentBeforeEdit: { value: "    a\n    b c\n     d" },
        stepFunction: async (editor) => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(5, 19); // "a[\nb c\n ]d"
            await press(["shift", "tab"]);
            await compareHighlightedContent(
                getContent(editor.editable),
                {
                    value: "a\nb c\n d",
                    textareaRange: [1, 7], // "a[\nb c\n ]d"
                },
                "The content was outdented a first time.",
                editor
            );
            // Remove the last remaining leading space.
            await press(["shift", "tab"]);
        },
        contentAfterEdit: {
            value: "a\nb c\nd",
            textareaRange: [1, 6], // "a[\nb c\n]d"
        },
        config: configWithEmbeddings,
    });
});

test.tags("focus required");
test("can switch between code blocks without issues", async () => {
    const { editor } = await setupEditor(`<p>ab</p><pre>de</pre><p>gh</p><pre>jk</pre>`, {
        config: configWithEmbeddings,
    });
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>ab</p>",
                wrapped: false,
            },
            {
                value: "de",
            },
            {
                value: "<p>gh</p>",
                wrapped: false,
            },
            { value: "jk" },
        ],
        "The content was highlighted",
        editor
    );
    const [p1, textarea1, p2, textarea2] = editor.document.querySelectorAll("p, textarea");
    await click(textarea1);
    testTextareaRange(editor, { el: textarea1, value: "de", range: 2 });
    await click(textarea2);
    testTextareaRange(editor, { el: textarea2, value: "jk", range: 2 });
    // Action 1: insert "l" in second pre.
    await press("l");
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>ab</p>",
                wrapped: false,
            },
            {
                value: "de",
            },
            {
                value: "<p>gh</p>",
                wrapped: false,
            },
            {
                value: "jkl",
                textareaRange: 3,
            },
        ],
        `1. Inserted "l" into the second pre and highlighted it.`,
        editor
    );
    await click(textarea1);
    testTextareaRange(editor, { el: textarea1, value: "de", range: 2 });
    // Action 2: insert "f" in first pre.
    await press("f");
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>ab</p>",
                wrapped: false,
            },
            {
                value: "def",
                textareaRange: 3,
            },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl" },
        ],
        `2. Inserted "f" into the first pre and highlighted it.`,
        editor
    );
    await click(p1);
    editor.shared.selection.setCursorEnd(p1);
    // Action 3: insert "c" in first paragraph.
    await insertText(editor, "c");
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>abc[]</p>",
                wrapped: false,
            },
            {
                value: "def",
            },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl" },
        ],
        `3. Inserted "c" into the first paragraph.`,
        editor
    );
    await click(p2);
    editor.shared.selection.setCursorEnd(p2);
    // Action 4: insert "i" in second paragraph.
    await insertText(editor, "i");
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>abc</p>",
                wrapped: false,
            },
            {
                value: "def",
            },
            {
                value: "<p>ghi[]</p>",
                wrapped: false,
            },
            { value: "jkl" },
        ],
        `4. Inserted "i" into the second paragraph.`,
        editor
    );
    // Action 5: change the language of first textarea.
    await changeLanguage(textarea1, "Plain Text", "Javascript");
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>abc</p>",
                wrapped: false,
            },
            {
                value: "def",
                language: "javascript",
                textareaRange: 3,
            },
            { value: "<p>ghi</p>", wrapped: false },
            { value: "jkl" },
        ],
        `5. Changed the language of the first textarea to "javascript".`,
        editor
    );
    // Action 6: change the language of second textarea.
    await changeLanguage(textarea2, "Plain Text", "Python");
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "<p>abc</p>",
                wrapped: false,
            },
            {
                value: "def",
                language: "javascript",
            },
            {
                value: "<p>ghi</p>",
                wrapped: false,
            },
            {
                value: "jkl",
                language: "python",
                textareaRange: 3,
            },
        ],
        `6. Changed the language of the second textarea to "python".`,
        editor
    );

    // UNDO
    // ----

    // UNDO action 6: change the language of second textarea.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            { value: "def", language: "javascript" },
            { value: "<p>ghi</p>", wrapped: false },
            { value: "jkl", textareaRange: 3 },
        ],
        // TODO: is it correct to not move the focus?
        `Undo 6 changed back the language of the second textarea to "plaintext" (without losing the current focus, editor).`,
        editor
    );
    // UNDO action 5: change the language of first textarea.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            { value: "def", textareaRange: 3 },
            { value: "<p>ghi</p>", wrapped: false },
            { value: "jkl" },
        ],
        // TODO: is it correct to move the focus?
        `Undo 5 changed back the language of the first textarea to "plaintext" (and move the focus to the last focused textarea, editor).`,
        editor
    );
    // UNDO action 4: insert "i" in second paragraph.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            { value: "def" },
            { value: "<p>gh[]</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Undo 4 removed the "i" from the second paragraph.`,
        editor
    );
    // UNDO action 3: insert "c" in first paragraph.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>ab[]</p>", wrapped: false },
            { value: "def" },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Undo 3 removed the "c" from the first paragraph.`,
        editor
    );
    // UNDO action 2: insert "f" in first pre.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>ab</p>", wrapped: false },
            { value: "de", textareaRange: 2 },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Undo 2 removed the "f" from the first pre and un-highlighted it.`,
        editor
    );
    // UNDO action 1: insert "l" in second pre.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>ab</p>", wrapped: false },
            { value: "de" },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jk", textareaRange: 2 },
        ],
        `Undo 1 removed the "l" from the second pre and un-highlighted it.`,
        editor
    );
    // UNDO nothing.
    await press(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>ab</p>", wrapped: false },
            { value: "de" },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jk", textareaRange: 2 },
        ],
        "Undo did nothing.",
        editor
    );

    // REDO
    // ----

    // REDO action 1: insert "l" in second pre.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>ab</p>", wrapped: false },
            { value: "de" },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl", textareaRange: 3 },
        ],
        `Redo 1 reinserted "l" into the second pre and re-highlighted it.`,
        editor
    );
    // REDO action 2: insert "f" in first pre.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>ab</p>", wrapped: false },
            { value: "def", textareaRange: 3 },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Redo 2 reinserted "f" into the first pre and re-highlighted it.`,
        editor
    );
    // REDO action 3: insert "c" in first paragraph.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc[]</p>", wrapped: false },
            { value: "def" },
            { value: "<p>gh</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Redo 3 reinserted "c" into the first paragraph.`,
        editor
    );
    // REDO action 4: insert "i" in second paragraph.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            { value: "def" },
            { value: "<p>ghi[]</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Redo 4 reinserted "i" into the second paragraph.`,
        editor
    );
    // REDO action 5: change the language of first textarea.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            {
                value: "def",
                language: "javascript",
                textareaRange: 3,
            },
            { value: "<p>ghi</p>", wrapped: false },
            { value: "jkl" },
        ],
        `Redo 5 changed back the language of the first textarea to "javascript".`,
        editor
    );
    // REDO action 6: change the language of second textarea.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            { value: "def", language: "javascript" },
            { value: "<p>ghi</p>", wrapped: false },
            {
                value: "jkl",
                language: "python",
                textareaRange: 3,
            },
        ],
        `Redo 6 changed back the language of the second textarea to "python".`,
        editor
    );
    // REDO nothing.
    await press(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            { value: "<p>abc</p>", wrapped: false },
            { value: "def", language: "javascript" },
            { value: "<p>ghi</p>", wrapped: false },
            {
                value: "jkl",
                language: "python",
                textareaRange: 3,
            },
        ],
        "Redo did nothing.",
        editor
    );
});

test.tags("focus required");
test("multiple ctrl+z in a highlighted code block undo changes in the block and any other changes before (all redone with ctrl+y or ctrl+shift+z)", async () => {
    const { editor } = await setupEditor(`<pre>some code</pre><p>hell[]</p>`, {
        config: configWithEmbeddings,
    });

    // Perform a series of actions to undo later.
    // ------------------------------------------

    const actions = [];
    const listActions = (...actionNumbers) =>
        actionNumbers
            .map((actionNumber) => `${actionNumber}. ${actions[actionNumber - 1]}`)
            .join("\n");

    // Perform a series of actions to undo later.
    // ------------------------------------------

    // Write in the P.
    actions.push("type: insert 'o' into the paragraph", "type: insert '!' into the paragraph");
    await insertText(editor, "o!"); // <wrapper><pre>some code</pre></wrapper><p>hello![]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
            },
            { value: "<p>hello![]</p>", wrapped: false },
        ],
        listActions(1, 2),
        editor
    );
    // Change the language -> code gets highlighted.
    actions.push("language: change the language to javascript and highlight the code");
    const textarea = queryOne("textarea");
    await changeLanguage(textarea, "Plain Text", "Javascript"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
                language: "javascript",
                textareaRange: 9,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        listActions(3),
        editor
    );
    // Write in the TEXTAREA.
    actions.push("type: insert 'n' into the pre", "type: insert 'o' into the pre");
    await click("textarea");
    await press("n"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("o"); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeno",
                language: "javascript",
                textareaRange: 11,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        listActions(4, 5),
        editor
    );
    actions.push(
        "type: remove 'o' from the pre",
        "type: remove 'n' from the pre",
        "type: insert 'y' into the pre",
        "type: insert 'e' into the pre",
        "type: insert 's' into the pre"
    );
    await press("Backspace"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("Backspace"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await press("y"); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press("e"); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press("s"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyes",
                language: "javascript",
                textareaRange: 12,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        listActions(6, 7, 8, 9, 10),
        editor
    );
    // Write in the P again.
    actions.push("type: insert 'o' into the paragraph", "type: insert 'k' into the paragraph");
    editor.shared.selection.setCursorEnd(queryOne("p"));
    await pointerUp("p"); // todo: needed?
    await insertText(editor, "ok"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok[]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyes",
                language: "javascript",
            },
            { value: "<p>hello!ok[]</p>", wrapped: false },
        ],
        listActions(11, 12),
        editor
    );
    // Write in the TEXTAREA again.
    actions.push("type: insert 'h' into the pre");
    await click("textarea");
    await press("h"); // <wrapper><highlight><pre>some codeyesh</pre></highlight></wrapper><p>hello!ok[]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyesh",
                language: "javascript",
                textareaRange: 13,
            },
            { value: "<p>hello!ok</p>", wrapped: false },
        ],
        listActions(13),
        editor
    );

    // Undo everything.
    // ----------------

    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyes",
                language: "javascript",
                textareaRange: 12,
            },
            { value: "<p>hello!ok</p>", wrapped: false },
        ],
        `undo:\n${listActions(13)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o[]</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello![]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyes",
                language: "javascript",
            },
            { value: "<p>hello![]</p>", wrapped: false },
        ],
        `undo:\n${listActions(12, 11)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
                language: "javascript",
                textareaRange: 9,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `undo:\n${listActions(10, 9, 8)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeno",
                language: "javascript",
                textareaRange: 11,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `undo:\n${listActions(7, 6)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",

                language: "javascript",
                textareaRange: 9,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `undo:\n${listActions(5, 4)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
                textareaRange: 9,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `undo:\n${listActions(3)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
            },
            { value: "<p>hell[]</p>", wrapped: false },
        ],
        `undo:\n${listActions(2, 1)}`,
        editor
    );
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
            },
            { value: "<p>hell[]</p>", wrapped: false },
        ],
        "undo: should have done nothing",
        editor
    );

    // Redo everything.
    // ----------------

    await press(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await press(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [{ value: "some code" }, { value: "<p>hello![]</p>", wrapped: false }],
        `redo:\n${listActions(1, 2)}`,
        editor
    );
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",

                language: "javascript",
                textareaRange: 9,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `redo:\n${listActions(3)}`,
        editor
    );
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeno",

                language: "javascript",
                textareaRange: 11,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `redo:\n${listActions(4, 5)}`,
        editor
    );
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some code",
                language: "javascript",
                textareaRange: 9,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `redo:\n${listActions(6, 7)}`,
        editor
    );
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyes",

                language: "javascript",
                textareaRange: 12,
            },
            { value: "<p>hello!</p>", wrapped: false },
        ],
        `redo:\n${listActions(8, 9, 10)}`,
        editor
    );
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o</p>
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyes",

                language: "javascript",
            },
            { value: "<p>hello!ok[]</p>", wrapped: false },
        ],
        `redo:\n${listActions(11, 12)}`,
        editor
    );
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyesh",

                language: "javascript",
                textareaRange: 13,
            },
            { value: "<p>hello!ok</p>", wrapped: false },
        ],
        `redo:\n${listActions(13)}`,
        editor
    );
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        [
            {
                value: "some codeyesh",

                language: "javascript",
                textareaRange: 13,
            },
            { value: "<p>hello!ok</p>", wrapped: false },
        ],
        "redo: should have done nothing",
        editor
    );
});
