import { beforeEach, expect, test } from "@odoo/hoot";
import { getContent, setSelection } from "./_helpers/selection";
import { animationFrame, click, press, queryOne, waitFor } from "@odoo/hoot-dom";
import { insertText, splitBlock } from "./_helpers/user_actions";
import {
    compareHighlightedContent,
    highlightedPre,
    patchPrism,
    testTextareaRange,
} from "./_helpers/syntax_highlighting";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { setupEditor, testEditor } from "./_helpers/editor";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { unformat } from "./_helpers/format";
import { parseHTML } from "@html_editor/utils/html";

// Press a key combination, then wait for useEffect to kick in.
const pressAndWait = async (...args) => {
    await press(...args);
    await animationFrame(); // wait for effect
};

const insertPre = async (editor) => {
    await insertText(editor, "/code");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Code");
    await pressAndWait("enter");
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
    await animationFrame(); // wait for effect
};

const configWithEmbeddings = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};
const testEditorWithHighlightedContent = async (config) =>
    await testEditor({
        ...config,
        compareFunction: compareHighlightedContent,
        config: configWithEmbeddings,
    });

beforeEach(patchPrism);

test("starting edition with a pre activates syntax highlighting", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>some code</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "some code" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            await pressAndWait(["ctrl", "z"]);
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "some code" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>', // Undo did nothing.
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">some code</pre>`,
    });
});

test("starting edition with a pre activates syntax highlighting (with dataset values)", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: `<pre data-language-id="javascript">Hello world!</pre>`,
        // The DIV should now be filled with a highlighted pre and a textarea,
        // the respective values of which match the dataset.
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "Hello world!", language: "javascript" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async (editor) => {
            await pressAndWait(["ctrl", "z"]);
            await compareHighlightedContent(
                getContent(editor.editable),
                '<p data-selection-placeholder=""><br></p>' +
                    highlightedPre({ value: "Hello world!", language: "javascript" }) +
                    '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                "Undo should have done nothing.",
                editor
            );
            await click("textarea");
            await pressAndWait("a");
            await compareHighlightedContent(
                getContent(editor.editable),
                '<p data-selection-placeholder=""><br></p>' +
                    highlightedPre({
                        value: "Hello world!a",
                        language: "javascript",
                        textareaRange: 13, // "Hello world!a[]"
                    }) +
                    '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                "Should have written at the end of the textarea.",
                editor
            );
            await pressAndWait(["ctrl", "z"]);
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({
                value: "Hello world!",
                language: "javascript",
                textareaRange: 12, // "Hello world![]"
            }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>', // Undo did nothing.
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="javascript">Hello world!</pre>[]`,
    });
});

test("inserting a code block activates syntax highlighting plugin, typing triggers highlight", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<p>[]abc</p>",
        stepFunction: async (editor) => {
            await insertPre(editor);
            await compareHighlightedContent(
                getContent(editor.editable),
                '<p data-selection-placeholder=""><br></p>' +
                    highlightedPre({ value: "abc", textareaRange: 3 }) +
                    '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                "The syntax highlighting wrapper was inserted, the paragraph's content is its value and the selection in at the end of the textarea.",
                editor
            );
            await pressAndWait("d");
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "abcd", textareaRange: 4 }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>', // The change of value in the textarea is reflected in the pre.
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">abcd</pre>[]`,
    });
});

test("inserting an empty code block activates syntax highlighting plugin with an empty textarea", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<p><br>[]</p>",
        stepFunction: insertPre,
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "", textareaRange: 0 }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext"><br></pre>[]`,
    });
});

test("inserting a code block in an empty paragraph with a style placeholder activates syntax highlighting plugin with an empty textarea", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<p><br>[]</p>",
        stepFunction: async (editor) => {
            await pressAndWait(["ctrl", "b"]);
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
        contentAfterEdit: unformat(
            `<p><strong data-oe-zws-empty-inline="">\u200B</strong></p>
            ${highlightedPre({
                value: "", // There should be no content (the zws is stripped)
                textareaRange: 0,
            })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        contentAfter: `<p><br></p><pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext"><br></pre>[]`,
    });
});

test("inserting text and undo after an empty code block activates the syntax highlighting plugin with an empty textarea", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<p><br>[]</p>",
        stepFunction: async (editor) => {
            await insertPre(editor);
            await compareHighlightedContent(
                getContent(editor.editable),
                '<p data-selection-placeholder=""><br></p>' +
                    highlightedPre({ value: "", textareaRange: 0 }) +
                    '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                editor
            );
            const p = document.querySelector("p");
            setSelection({ anchorNode: p, anchorOffset: 0 });
            await insertText(editor, "a");
            await pressAndWait(["ctrl", "z"]);
        },
        contentAfterEdit:
            `<p data-selection-placeholder="" class="o-horizontal-caret o-we-hint" o-we-hint-text='Type "/" for commands'>[]<br></p>` +
            highlightedPre({ value: "" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `[]<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext"><br></pre>`,
    });
});

test("changing languages in a code block changes its highlighting", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>some code</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "some code", language: "plaintext" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            await changeLanguage(queryOne("textarea"), "Plain Text", "Javascript");
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({
                value: "some code",
                language: "javascript",
                textareaRange: 9,
            }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="javascript">some code</pre>[]`,
    });
});

test("should fill an empty pre", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>abc</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "abc" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            const textarea = queryOne("textarea");
            await click(textarea);
            textarea.select();
            await pressAndWait("backspace");
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "", textareaRange: 0 }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>', // Note: the BR is outside the highlight.
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext"><br></pre>[]`,
    });
});

test("should convert empty codeblock into base container on backspace", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre></pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            const textarea = queryOne("textarea");
            await click(textarea);
            await pressAndWait("Backspace");
        },
        contentAfterEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
        contentAfter: `<p>[]<br></p>`,
    });
});

test("the textarea should never contains zws", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>a\u200bb\ufeffc</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "abc" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            const textarea = queryOne("textarea");
            await click(textarea);
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "abc", textareaRange: 3 }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">abc</pre>[]`,
    });
});

test("can copy content with the copy button", async () => {
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>abc</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "abc" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
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
            await pressAndWait("d");
            testTextareaRange(editor, { el: textarea, value: "abcd", range: 4 });
            // Copy "abcd"
            await click(".o_code_toolbar .o_clipboard_button");
            expect.verifySteps(["abcd"]);
            textarea.focus();
            await animationFrame(); // wait for effect
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "abcd", textareaRange: 4 }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">abcd</pre>[]`,
    });
});

test("tab in code block inserts 4 spaces", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>code</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "code" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(2, 2); // "co[]de"
            await pressAndWait("tab");
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({
                value: "co    de",
                textareaRange: 6, // "co    []de"
            }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">co    de</pre>[]`,
    });
});

test("tab in selection in code block indents each selected line", async () => {
    const valueAfter = "    a\n    b c\n     d";
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>a<br>b c<br> d</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "a\nb c\n d" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async () => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(1, 7); // "a[\nb c\n ]d"
            await pressAndWait("tab");
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({
                value: valueAfter,
                textareaRange: [5, 19], // "    a[\n    b c\n     ]d"
            }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">${valueAfter.replaceAll(
            "\n",
            "<br>"
        )}</pre>[]`,
    });
});

test("shift+tab in code block outdents the current line", async () => {
    const valueAfter = "    some\nco    de\n    for you";
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>    some<br>       co    de<br>    for you</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "    some\n       co    de\n    for you" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async (editor) => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(22, 22); // "    some\n       co    []de\n    for you"
            await pressAndWait(["shift", "tab"]);
            await compareHighlightedContent(
                getContent(editor.editable),
                '<p data-selection-placeholder=""><br></p>' +
                    highlightedPre({
                        value: "    some\n   co    de\n    for you",
                        textareaRange: 18, // "    some\n   co    []de\n    for you"
                    }) +
                    '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                "The content was outdented a first time.",
                editor
            );
            await pressAndWait(["shift", "tab"]);
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({
                value: valueAfter,
                textareaRange: 15, // "    some\nco    []de\n    for you"
            }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">${valueAfter.replaceAll(
            "\n",
            "<br>"
        )}</pre>[]`,
    });
});

test("shift+tab in selection in code block outdents each selected line", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: "<pre>    a<br>    b c<br>     d</pre>",
        contentBeforeEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({ value: "    a\n    b c\n     d" }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        stepFunction: async (editor) => {
            await click("textarea");
            const textarea = queryOne("textarea");
            textarea.setSelectionRange(5, 19); // "a[\nb c\n ]d"
            await pressAndWait(["shift", "tab"]);
            await compareHighlightedContent(
                getContent(editor.editable),
                '<p data-selection-placeholder=""><br></p>' +
                    highlightedPre({
                        value: "a\nb c\n d",
                        textareaRange: [1, 7], // "a[\nb c\n ]d"
                    }) +
                    '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                "The content was outdented a first time.",
                editor
            );
            // Remove the last remaining leading space.
            await pressAndWait(["shift", "tab"]);
        },
        contentAfterEdit:
            '<p data-selection-placeholder=""><br></p>' +
            highlightedPre({
                value: "a\nb c\nd",
                textareaRange: [1, 6], // "a[\nb c\n]d"
            }) +
            '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">a<br>b c<br>d</pre>[]`,
    });
});

test.tags("focus required");
test("can switch between code blocks without issues", async () => {
    const { editor } = await setupEditor(`<p>ab</p><pre>de</pre><p>gh</p><pre>jk</pre>`, {
        config: configWithEmbeddings,
    });
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "de" })}
            <p>gh</p>
            ${highlightedPre({ value: "jk" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        "The content was highlighted",
        editor
    );
    const [p1, textarea1, p2, textarea2] = editor.document.querySelectorAll("p, textarea");
    await click(textarea1);
    testTextareaRange(editor, { el: textarea1, value: "de", range: 2 });
    await click(textarea2);
    testTextareaRange(editor, { el: textarea2, value: "jk", range: 2 });
    // Action 1: insert "l" in second pre.
    await pressAndWait("l");
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "de" })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl", textareaRange: 3 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `1. Inserted "l" into the second pre and highlighted it.`,
        editor
    );
    await click(textarea1);
    testTextareaRange(editor, { el: textarea1, value: "de", range: 2 });
    // Action 2: insert "f" in first pre.
    await pressAndWait("f");
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "def", textareaRange: 3 })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `2. Inserted "f" into the first pre and highlighted it.`,
        editor
    );
    await click(p1);
    editor.shared.selection.setCursorEnd(p1);
    // Action 3: insert "c" in first paragraph.
    await insertText(editor, "c");
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc[]</p>
            ${highlightedPre({ value: "def" })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `3. Inserted "c" into the first paragraph.`,
        editor
    );
    await click(p2);
    editor.shared.selection.setCursorEnd(p2);
    // Action 4: insert "i" in second paragraph.
    await insertText(editor, "i");
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def" })}
            <p>ghi[]</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `4. Inserted "i" into the second paragraph.`,
        editor
    );
    // Action 5: change the language of first textarea.
    await changeLanguage(textarea1, "Plain Text", "Javascript");
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", language: "javascript", textareaRange: 3 })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `5. Changed the language of the first textarea to "javascript".`,
        editor
    );
    // Action 6: change the language of second textarea.
    await changeLanguage(textarea2, "Plain Text", "Python");
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", language: "javascript" })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl", language: "python", textareaRange: 3 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `6. Changed the language of the second textarea to "python".`,
        editor
    );

    // UNDO
    // ----

    // UNDO action 6: change the language of second textarea.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", language: "javascript" })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl", textareaRange: 3 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        // TODO: is it correct to not move the focus?
        `Undo 6 changed back the language of the second textarea to "plaintext" (without losing the current focus, editor).`,
        editor
    );
    // UNDO action 5: change the language of first textarea.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", textareaRange: 3 })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        // TODO: is it correct to move the focus?
        `Undo 5 changed back the language of the first textarea to "plaintext" (and move the focus to the last focused textarea, editor).`,
        editor
    );
    // UNDO action 4: insert "i" in second paragraph.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def" })}
            <p>gh[]</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Undo 4 removed the "i" from the second paragraph.`,
        editor
    );
    // UNDO action 3: insert "c" in first paragraph.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab[]</p>
            ${highlightedPre({ value: "def" })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Undo 3 removed the "c" from the first paragraph.`,
        editor
    );
    // UNDO action 2: insert "f" in first pre.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "de", textareaRange: 2 })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Undo 2 removed the "f" from the first pre and un-highlighted it.`,
        editor
    );
    // UNDO action 1: insert "l" in second pre.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "de" })}
            <p>gh</p>
            ${highlightedPre({ value: "jk", textareaRange: 2 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Undo 1 removed the "l" from the second pre and un-highlighted it.`,
        editor
    );
    // UNDO nothing.
    await pressAndWait(["ctrl", "z"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "de" })}
            <p>gh</p>
            ${highlightedPre({ value: "jk", textareaRange: 2 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        "Undo did nothing.",
        editor
    );

    // REDO
    // ----

    // REDO action 1: insert "l" in second pre.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "de" })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl", textareaRange: 3 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Redo 1 reinserted "l" into the second pre and re-highlighted it.`,
        editor
    );
    // REDO action 2: insert "f" in first pre.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>ab</p>
            ${highlightedPre({ value: "def", textareaRange: 3 })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Redo 2 reinserted "f" into the first pre and re-highlighted it.`,
        editor
    );
    // REDO action 3: insert "c" in first paragraph.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc[]</p>
            ${highlightedPre({ value: "def" })}
            <p>gh</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Redo 3 reinserted "c" into the first paragraph.`,
        editor
    );
    // REDO action 4: insert "i" in second paragraph.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def" })}
            <p>ghi[]</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Redo 4 reinserted "i" into the second paragraph.`,
        editor
    );
    // REDO action 5: change the language of first textarea.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", language: "javascript", textareaRange: 3 })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Redo 5 changed back the language of the first textarea to "javascript".`,
        editor
    );
    // REDO action 6: change the language of second textarea.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", language: "javascript" })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl", language: "python", textareaRange: 3 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        `Redo 6 changed back the language of the second textarea to "python".`,
        editor
    );
    // REDO nothing.
    await pressAndWait(["ctrl", "y"]);
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p>abc</p>
            ${highlightedPre({ value: "def", language: "javascript" })}
            <p>ghi</p>
            ${highlightedPre({ value: "jkl", language: "python", textareaRange: 3 })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
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
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code" })}
            <p>hello![]</p>
        `),
        listActions(1, 2),
        editor
    );
    // Change the language -> code gets highlighted.
    actions.push("language: change the language to javascript and highlight the code");
    const textarea = queryOne("textarea");
    await changeLanguage(textarea, "Plain Text", "Javascript"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code", language: "javascript", textareaRange: 9 })}
            <p>hello!</p>
        `),
        listActions(3),
        editor
    );
    // Write in the TEXTAREA.
    actions.push("type: insert 'n' into the pre", "type: insert 'o' into the pre");
    await click("textarea");
    await pressAndWait("n"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait("o"); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeno", language: "javascript", textareaRange: 11 })}
            <p>hello!</p>
        `),
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
    await pressAndWait("Backspace"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait("Backspace"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait("y"); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait("e"); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait("s"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyes", language: "javascript", textareaRange: 12 })}
            <p>hello!</p>
        `),
        listActions(6, 7, 8, 9, 10),
        editor
    );
    // Write in the P again.
    actions.push("type: insert 'o' into the paragraph", "type: insert 'k' into the paragraph");
    const p = queryOne("p:not([data-selection-placeholder])");
    await click(p);
    editor.shared.selection.setCursorEnd(p);
    await insertText(editor, "ok"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok[]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyes", language: "javascript" })}
            <p>hello!ok[]</p>
        `),
        listActions(11, 12),
        editor
    );
    // Write in the TEXTAREA again.
    actions.push("type: insert 'h' into the pre");
    await click("textarea");
    await pressAndWait("h"); // <wrapper><highlight><pre>some codeyesh</pre></highlight></wrapper><p>hello!ok[]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyesh", language: "javascript", textareaRange: 13 })}
            <p>hello!ok</p>
        `),
        listActions(13),
        editor
    );

    // Undo everything.
    // ----------------

    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyes", language: "javascript", textareaRange: 12 })}
            <p>hello!ok</p>
        `),
        `undo:\n${listActions(13)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o[]</p>
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello![]</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyes", language: "javascript" })}
            <p>hello![]</p>
        `),
        `undo:\n${listActions(12, 11)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code", language: "javascript", textareaRange: 9 })}
            <p>hello!</p>
        `),
        `undo:\n${listActions(10, 9, 8)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeno", language: "javascript", textareaRange: 11 })}
            <p>hello!</p>
        `),
        `undo:\n${listActions(7, 6)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code", language: "javascript", textareaRange: 9 })}
            <p>hello!</p>
        `),
        `undo:\n${listActions(5, 4)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code", textareaRange: 9 })}
            <p>hello!</p>
        `),
        `undo:\n${listActions(3)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await pressAndWait(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code" })}
            <p>hell[]</p>
        `),
        `undo:\n${listActions(2, 1)}`,
        editor
    );
    await pressAndWait(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code" })}
            <p>hell[]</p>
        `),
        "undo: should have done nothing",
        editor
    );

    // Redo everything.
    // ----------------

    await pressAndWait(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await pressAndWait(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code" })}
            <p>hello![]</p>`
        ),
        `redo:\n${listActions(1, 2)}`,
        editor
    );
    await pressAndWait(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code", language: "javascript", textareaRange: 9 })}
            <p>hello!</p>
        `),
        `redo:\n${listActions(3)}`,
        editor
    );
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeno", language: "javascript", textareaRange: 11 })}
            <p>hello!</p>
        `),
        `redo:\n${listActions(4, 5)}`,
        editor
    );
    await pressAndWait(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some code", language: "javascript", textareaRange: 9 })}
            <p>hello!</p>
        `),
        `redo:\n${listActions(6, 7)}`,
        editor
    );
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyes", language: "javascript", textareaRange: 12 })}
            <p>hello!</p>
        `),
        `redo:\n${listActions(8, 9, 10)}`,
        editor
    );
    await pressAndWait(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o</p>
    await pressAndWait(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyes", language: "javascript" })}
            <p>hello!ok[]</p>
        `),
        `redo:\n${listActions(11, 12)}`,
        editor
    );
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyesh", language: "javascript", textareaRange: 13 })}
            <p>hello!ok</p>
        `),
        `redo:\n${listActions(13)}`,
        editor
    );
    await pressAndWait(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await pressAndWait(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(`
            <p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "some codeyesh", language: "javascript", textareaRange: 13 })}
            <p>hello!ok</p>
        `),
        "redo: should have done nothing",
        editor
    );
});

test("can copy/paste a highlighted code block", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: unformat(
            `<p>[ab</p>
        <pre data-language-id="javascript">some code</pre>
        <p>cd]</p>`
        ),
        contentBeforeEdit: unformat(
            `<p>[ab</p>
            ${highlightedPre({ language: "javascript", value: "some code" })}
            <p>cd]</p>`
        ),
        stepFunction: async (editor) => {
            const clipboardData = new DataTransfer();
            await press(["ctrl", "c"], { dataTransfer: clipboardData });
            const copiedValue = unformat(
                `<p>ab</p>
                <pre data-embedded="readonlySyntaxHighlighting" data-language-id="javascript">some code</pre>
                <p>cd</p>`
            );
            expect(clipboardData.getData("text/html")).toBe(copiedValue);
            await press("delete");
            expect(getContent(editor.editable)).toBe(
                `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
            );
            editor.shared.dom.insert(parseHTML(editor.document, copiedValue));
            editor.shared.history.addStep();
            await animationFrame();
        },
        contentAfterEdit: unformat(
            `<p>ab</p>
            ${highlightedPre({ language: "javascript", value: "some code" })}
            <p>cd[]</p>`
        ),
        contentAfter: unformat(
            `<p>ab</p>
            <pre data-embedded="readonlySyntaxHighlighting" data-language-id="javascript">some code</pre>
            <p>cd[]</p>`
        ),
    });
});

test("invisible whitespace gets trimmed before changing tag to pre", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: `<p>
            hel[]lo
        </p>`,
        stepFunction: insertPre,
        contentAfter: `<pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">hello</pre>[]`,
    });
});

test("can write in a highlighted code block within a nested list", async () => {
    await testEditorWithHighlightedContent({
        contentBefore: unformat(
            `<p>a</p>
            <ul>
                <li class="oe-nested">
                    <ul>
                        <li>
                            <pre>some code</pre>
                        </li>
                    </ul>
                </li>
            </ul>
            <p>b</p>`
        ),
        stepFunction: async () => {
            await click("textarea");
            await pressAndWait("x");
            await pressAndWait("y");
        },
        contentAfter: unformat(
            `<p>a</p>
            <ul>
                <li class="oe-nested">
                    <ul>
                        <li>
                            <pre data-embedded="readonlySyntaxHighlighting" data-language-id="plaintext">some codexy</pre>[]
                        </li>
                    </ul>
                </li>
            </ul>
            <p>b</p>`
        ),
    });
});

test("restore paragraph from code block", async () => {
    await testEditor({
        contentBefore: "<pre>[]abc</pre>",
        stepFunction: async () => {
            await click(".o_code_toolbar span.fa-paragraph");
        },
        contentAfterEdit: "<p>[]abc</p>",
        contentAfter: `<p>[]abc</p>`,
        config: configWithEmbeddings,
    });
});

test("should keep textarea focused when changing code block language", async () => {
    const { editor } = await setupEditor(`<pre>ab</pre>`, {
        config: configWithEmbeddings,
    });

    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "ab" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        "Initial code block is highlighted",
        editor
    );

    // Focus the textarea inside the code block
    const textarea = editor.document.querySelector("textarea");
    await click(textarea);
    expect(editor.document.activeElement).toBe(textarea);
    const from = "Plain Text";
    const to = "Javascript";
    // Wait until the language selector button is available in the toolbar
    await waitFor(`.o_code_toolbar button[name='language'][title='${from}']`);
    const dropdownButton = document.querySelector(
        `.o_code_toolbar button[name='language'][title='${from}']`
    );
    // Explicitly focus the dropdown button before opening it
    dropdownButton.focus();
    await click(dropdownButton);
    // Language selector dropdown should open.
    await waitFor(`.o_language_selector .o-dropdown-item[name='${to}']`);
    await click(`.o_language_selector .o-dropdown-item[name='${to}']`);
    // Code Toolbar should show the new language name.
    await waitFor(`.o_code_toolbar button[name='language'][title='${to}']`);
    // Ensure focus is restored to the textarea after the dropdown closes
    expect(document.activeElement).toBe(textarea);
});

test("should keep textarea focused after copying code content", async () => {
    const { editor } = await setupEditor(`<pre>ab</pre>`, {
        config: configWithEmbeddings,
    });
    await compareHighlightedContent(
        getContent(editor.editable),
        unformat(
            `<p data-selection-placeholder=""><br></p>
            ${highlightedPre({ value: "ab" })}
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        "Initial code block is highlighted",
        editor
    );

    // Focus the textarea inside the code block
    const textarea = editor.document.querySelector("textarea");
    await click(textarea);
    expect(editor.document.activeElement).toBe(textarea);

    // Wait for the code toolbar and trigger the copy action
    await waitFor(".o_code_toolbar");
    await click(".o_code_toolbar .o_clipboard_button");

    // Ensure focus remains on the textarea after copying
    expect(document.activeElement).toBe(textarea);
});
