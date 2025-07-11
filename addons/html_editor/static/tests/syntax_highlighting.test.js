import { beforeEach, expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { animationFrame, click, press, queryOne, waitFor } from "@odoo/hoot-dom";
import { insertText, splitBlock } from "./_helpers/user_actions";
import {
    getPreStyle,
    patchPrism,
    SYNTAX_HIGHLIGHTING_WRAPPER,
} from "./_helpers/syntax_highlighting";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

const testSelectionInTextarea = (editor, textarea, value, start, end = start) => {
    const { anchorNode, anchorOffset, focusNode, focusOffset } = editor.document.getSelection();
    expect({
        activeElement: editor.document.activeElement,
        anchorTarget: anchorNode.childNodes[anchorOffset],
        focusTarget: focusNode.childNodes[focusOffset],
        textareaValue: textarea.value,
        textareaSelection: [textarea.selectionStart, textarea.selectionEnd],
    }).toEqual(
        {
            activeElement: textarea,
            anchorTarget: textarea,
            focusTarget: textarea,
            textareaValue: value,
            textareaSelection: [start, end],
        },
        { message: "Selection should be correct in the textarea." }
    );
};

const changeLanguage = async (textarea, from, to) => {
    await click(textarea);
    await animationFrame();
    // Code Toolbar should open.
    await waitFor(".o_code_toolbar");
    await click(`.o_code_toolbar button[name='language'][title='${from}']`);
    // Language selector dropdown should open.
    await waitFor(".o_language_selector");
    await click(`.o_language_selector .o-dropdown-item[name='${to}']`);
    // Code Toolbar should show the new language name.
    await waitFor(`.o_code_toolbar button[name='language'][title='${to}']`);
};

beforeEach(patchPrism);

test("starting edition with a code block activates syntax highlighting", async () => {
    const { editor, el } = await setupEditor(`<pre>some code[]</pre>`);
    const preStyle = getPreStyle(editor);
    await animationFrame();
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("some code", {
            highlight: false,
            focused: false,
            preStyle,
        }) + "[]"
    );
});

test("inserting a code block activates syntax highlighting plugin, typing triggers highlight", async () => {
    const { editor, el } = await setupEditor("<p>[]abc</p>");
    await insertText(editor, "/code");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Code");
    await press("enter");
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("abc", { highlight: false, focused: true }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    const textarea = editor.document.querySelector("textarea");
    // The paragraph's content was transferred to the textarea and its selection is at the end of its content.
    testSelectionInTextarea(editor, textarea, "abc", 3);
    await press("d");
    expect(getContent(el)).toBe(SYNTAX_HIGHLIGHTING_WRAPPER(`abcd`, { preStyle, focused: true }), {
        message:
            "The change of value in the textarea is reflected in the pre, which is now highlighted.",
    });
    testSelectionInTextarea(editor, textarea, "abcd", 4);
});

test("inserting an empty code block activates syntax highlighting plugin with an empty textarea", async () => {
    const { editor, el } = await setupEditor("<p><br>[]</p>");
    await insertText(editor, "/code");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Code");
    await press("enter");
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("<br>", { highlight: false, focused: true }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    const textarea = editor.document.querySelector("textarea");
    testSelectionInTextarea(editor, textarea, "", 0); // There should be no content.
    await press("a");
    expect(getContent(el)).toBe(SYNTAX_HIGHLIGHTING_WRAPPER(`a`, { preStyle, focused: true }), {
        message:
            "The change of value in the textarea is reflected in the pre, which is now highlighted.",
    });
    testSelectionInTextarea(editor, textarea, "a", 1);
});

test("inserting a code block in an empty paragraph with a style placeholder activates syntax highlighting plugin with an empty textarea", async () => {
    const { editor, el } = await setupEditor("<p><br>[]</p>");
    await press(["ctrl", "b"]);
    expect(getContent(el)).toBe(
        `<p o-we-hint-text='Type "/" for commands' class="o-we-hint"><strong data-oe-zws-empty-inline="">[]\u200B</strong></p>`,
        {
            message: "The style placeholder was inserted.",
        }
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><strong data-oe-zws-empty-inline="">\u200B</strong></p>` +
            `<p o-we-hint-text='Type "/" for commands' class="o-we-hint"><strong data-oe-zws-empty-inline="">[]\u200B</strong></p>`,
        {
            message: "The paragraph was split.",
        }
    );
    await insertText(editor, "/code");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Code");
    await press("enter");
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        `<p><strong data-oe-zws-empty-inline="">\u200B</strong></p>` +
            SYNTAX_HIGHLIGHTING_WRAPPER(`<strong data-oe-zws-empty-inline="">\u200B</strong>`, {
                highlight: false,
                focused: true,
            }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    const textarea = editor.document.querySelector("textarea");
    testSelectionInTextarea(editor, textarea, "", 0); // There should be no content (the zws is stripped).
    await press("a");
    expect(getContent(el)).toBe(
        `<p><strong data-oe-zws-empty-inline="">\u200B</strong></p>` +
            SYNTAX_HIGHLIGHTING_WRAPPER("a", { preStyle, focused: true }),
        {
            message:
                "The change of value in the textarea is reflected in the pre, which is now highlighted. The empty strong element was removed from the code block.",
        }
    );
    testSelectionInTextarea(editor, textarea, "a", 1);
});

test("changing languages in a code block changes its highlighting", async () => {
    const { editor, el } = await setupEditor(`<pre>some code[]</pre>`);
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, { highlight: false, preStyle }) + "[]",
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    await changeLanguage(queryOne("textarea"), "Plain Text", "Javascript");
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "javascript",
            preStyle,
            focused: true,
        }),
        {
            message: "The code was highlighted in javascript.",
        }
    );
});

test("multiple ctrl+z in a highlighted code block undo changes in the block and any other changes before (all redone with ctrl+y or ctrl+shift+z)", async () => {
    const { editor, el } = await setupEditor(`<pre>some code</pre><p>hell[]</p>`);
    const preStyle = getPreStyle(editor);

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
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, { highlight: false, preStyle }) +
            "<p>hello![]</p>",
        { message: listActions(1, 2) }
    );
    // Change the language -> code gets highlighted.
    actions.push("language: change the language to javascript and highlight the code");
    const textarea = queryOne("textarea");
    await changeLanguage(textarea, "Plain Text", "Javascript"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        { message: listActions(3) }
    );
    testSelectionInTextarea(editor, textarea, "some code", textarea.value.length);
    // Write in the TEXTAREA.
    actions.push("type: insert 'n' into the pre", "type: insert 'o' into the pre");
    await click("textarea");
    await press("n"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("o"); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        { message: listActions(4, 5) }
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
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        {
            message: listActions(6, 7, 8, 9, 10),
        }
    );
    testSelectionInTextarea(editor, textarea, "some codeyes", textarea.value.length);
    // Write in the P again.
    actions.push("type: insert 'o' into the paragraph", "type: insert 'k' into the paragraph");
    await click("p");
    setSelection({ anchorNode: queryOne("p").firstChild, anchorOffset: 6 });
    await insertText(editor, "ok"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok[]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, { language: "javascript", preStyle }) +
            "<p>hello!ok[]</p>",
        {
            message: listActions(11, 12),
        }
    );
    // Write in the TEXTAREA again.
    actions.push("type: insert 'h' into the pre");
    await click("textarea");
    await press("h"); // <wrapper><highlight><pre>some codeyesh</pre></highlight></wrapper><p>hello!ok[]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyesh`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!ok</p>",
        { message: listActions(13) }
    );
    testSelectionInTextarea(editor, textarea, "some codeyesh", textarea.value.length);

    // Undo everything.
    // ----------------

    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!ok</p>",
        {
            message: `undo:\n${listActions(13)}`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some codeyes", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o[]</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello![]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, { language: "javascript", preStyle }) +
            "<p>hello![]</p>",
        {
            message: `undo:\n${listActions(12, 11)}`,
        }
    );
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        {
            message: `undo:\n${listActions(10, 9, 8)}`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some code", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        {
            message: `undo:\n${listActions(7, 6)}`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some codeno", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        {
            message: `undo:\n${listActions(5, 4)}`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some code", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "plaintext",
            highlight: false,
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        {
            message: `undo:\n${listActions(3)}`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some code", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "plaintext",
            highlight: false,
            preStyle,
        }) + "<p>hell[]</p>",
        {
            message: `undo:\n${listActions(2, 1)}`,
        }
    );
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "plaintext",
            highlight: false,
            preStyle,
        }) + "<p>hell[]</p>",
        {
            message: `undo: should have done nothing`,
        }
    );

    // Redo everything.
    // ----------------

    await press(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await press(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "plaintext",
            highlight: false,
            preStyle,
        }) + "<p>hello![]</p>",
        {
            message: `redo:\n${listActions(1, 2)}`,
        }
    );
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        { message: `redo:\n${listActions(3)}` }
    );
    testSelectionInTextarea(editor, textarea, "some code", textarea.value.length);
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        { message: `redo:\n${listActions(4, 5)}` }
    );
    testSelectionInTextarea(editor, textarea, "some codeno", textarea.value.length);
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        { message: `redo:\n${listActions(6, 7)}` }
    );
    testSelectionInTextarea(editor, textarea, "some code", textarea.value.length);
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!</p>",
        { message: `redo:\n${listActions(8, 9, 10)}` }
    );
    testSelectionInTextarea(editor, textarea, "some codeyes", textarea.value.length);
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o</p>
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, { language: "javascript", preStyle }) +
            "<p>hello!ok[]</p>",
        { message: `redo:\n${listActions(11, 12)}` }
    );
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyesh`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!ok</p>",
        {
            message: `redo:\n${listActions(13)}`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some codeyesh", textarea.value.length);
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyesh`, {
            language: "javascript",
            preStyle,
            focused: true,
        }) + "<p>hello!ok</p>",
        {
            message: `redo: should have done nothing`,
        }
    );
    testSelectionInTextarea(editor, textarea, "some codeyesh", textarea.value.length);
});

test("tab in code block inserts 4 spaces", async () => {
    const { editor, el } = await setupEditor(`<pre>code</pre>`);
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`code`, { highlight: false, preStyle }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    await click("textarea");
    const textarea = queryOne("textarea");
    textarea.setSelectionRange(2, 2);
    testSelectionInTextarea(editor, textarea, "code", 2); // "co[]de"
    await press("tab");
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`co    de`, {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        })
    );
    testSelectionInTextarea(editor, textarea, "co    de", 6); // "co    []de"
});

test("tab in selection in code block indents each selected line", async () => {
    const { editor, el } = await setupEditor(`<pre>code</pre>`);
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("code", { highlight: false, preStyle }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    await click("textarea");
    const textarea = queryOne("textarea");
    textarea.select();
    testSelectionInTextarea(editor, textarea, "code", 0, 4);
    await press("a");
    await press("Enter");
    await press("b");
    await press("Space");
    await press("c");
    await press("Enter");
    await press("Space");
    await press("d");
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("a<br>b c<br> d", {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        }),
        {
            message: "The text was inserted and highlighted.",
        }
    );
    textarea.setSelectionRange(1, 7); // "a[\nb c\n ]d"
    testSelectionInTextarea(editor, textarea, "a\nb c\n d", 1, 7); // "    a[\n    b c\n     ]d"
    await press("tab");
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("    a<br>    b c<br>     d", {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        })
    );
    testSelectionInTextarea(editor, textarea, "    a\n    b c\n     d", 5, 19); // "    a[\n    b c\n     ]d"
});

test("shift+tab in code block outdents the current line", async () => {
    const { editor, el } = await setupEditor(
        `<pre>    some<br>       co    de<br>    for you</pre>`
    );
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`    some<br>       co    de<br>    for you`, {
            highlight: false,
            preStyle,
        }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    await click("textarea");
    const textarea = queryOne("textarea");
    textarea.setSelectionRange(22, 22); // "    some\n       co    []de\n    for you"
    testSelectionInTextarea(editor, textarea, "    some\n       co    de\n    for you", 22); // "    some\n       co    []de\n    for you"
    await press(["shift", "tab"]);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`    some<br>   co    de<br>    for you`, {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        })
    );
    testSelectionInTextarea(editor, textarea, "    some\n   co    de\n    for you", 18); // "    some\n   co    []de\n    for you"
    await press(["shift", "tab"]);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`    some<br>co    de<br>    for you`, {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        })
    );
    testSelectionInTextarea(editor, textarea, "    some\nco    de\n    for you", 15); // "    some\nco    []de\n    for you"
});

test("shift+tab in selection in code block outdents each selected line", async () => {
    const { editor, el } = await setupEditor(`<pre>    a<br>    b c<br>     d</pre>`);
    const preStyle = getPreStyle(editor);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("    a<br>    b c<br>     d", { highlight: false, preStyle }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    await click("textarea");
    const textarea = queryOne("textarea");
    textarea.setSelectionRange(5, 19); // "a[\nb c\n ]d"
    testSelectionInTextarea(editor, textarea, "    a\n    b c\n     d", 5, 19); // "    a[\n    b c\n     ]d"
    await press(["shift", "tab"]);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("a<br>b c<br> d", {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        })
    );
    testSelectionInTextarea(editor, textarea, "a\nb c\n d", 1, 7);
    await press(["shift", "tab"]);
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("a<br>b c<br>d", {
            language: "plaintext",
            highlight: true,
            preStyle,
            focused: true,
        }),
        { message: "Removed the last remaining leading space." }
    );
    testSelectionInTextarea(editor, textarea, "a\nb c\nd", 1, 6);
});

test("can switch between code blocks without issues", async () => {
    const { editor, el } = await setupEditor(`<p>ab</p><pre>de</pre><p>gh</p><pre>jk</pre>`);
    const preStyle = getPreStyle(editor);
    await animationFrame();
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("de", {
                highlight: false,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jk", {
                highlight: false,
                preStyle,
            })
    );
    const [p1, textarea1, p2, textarea2] = editor.document.querySelectorAll("p, textarea");
    await click(textarea1);
    testSelectionInTextarea(editor, textarea1, "de", 2);
    await click(textarea2);
    testSelectionInTextarea(editor, textarea2, "jk", 2);
    // Action 1: insert "l" in second pre.
    await press("l");
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("de", {
                highlight: false,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                focused: true,
                preStyle,
            }),
        { message: `1. Inserted "l" into the second pre and highlighted it.` }
    );
    testSelectionInTextarea(editor, textarea2, "jkl", 3);
    await click(textarea1);
    testSelectionInTextarea(editor, textarea1, "de", 2);
    // Action 2: insert "f" in first pre.
    await press("f");
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                focused: true,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `2. Inserted "f" into the first pre and highlighted it.` }
    );
    testSelectionInTextarea(editor, textarea1, "def", 3);
    await click(p1);
    editor.shared.selection.setCursorEnd(p1);
    // Action 3: insert "c" in first paragraph.
    await insertText(editor, "c");
    expect(getContent(el)).toBe(
        "<p>abc[]</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `3. Inserted "c" into the first paragraph.` }
    );
    await click(p2);
    editor.shared.selection.setCursorEnd(p2);
    // Action 4: insert "i" in second paragraph.
    await insertText(editor, "i");
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
            }) +
            "<p>ghi[]</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `4. Inserted "i" into the second paragraph.` }
    );
    // Action 5: change the language of first textarea.
    await changeLanguage(textarea1, "Plain Text", "Javascript");
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                language: "javascript",
                highlight: true,
                focused: true,
                preStyle,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `5. Changed the language of the first textarea to "javascript".` }
    );
    // Action 6: change the language of second textarea.
    await changeLanguage(textarea2, "Plain Text", "Python");
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                language: "javascript",
                highlight: true,
                preStyle,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                language: "python",
                highlight: true,
                focused: true,
                preStyle,
            }),
        { message: `6. Changed the language of the second textarea to "python".` }
    );

    // UNDO
    // ----

    // UNDO action 6: change the language of second textarea.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                language: "javascript",
                highlight: true,
                preStyle,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                focused: true,
                preStyle,
            }),
        {
            // TODO: is it correct to not move the focus?
            message: `Undo 6 changed back the language of the second textarea to "plaintext" (without losing the current focus).`,
        }
    );
    // UNDO action 5: change the language of first textarea.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
                focused: true,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        {
            // TODO: is it correct to move the focus?
            message: `Undo 5 changed back the language of the first textarea to "plaintext" (and move the focus to the last focused textarea).`,
        }
    );
    // UNDO action 4: insert "i" in second paragraph.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
            }) +
            "<p>gh[]</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Undo 4 removed the "i" from the second paragraph.` }
    );
    // UNDO action 3: insert "c" in first paragraph.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>ab[]</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Undo 3 removed the "c" from the first paragraph.` }
    );
    // UNDO action 2: insert "f" in first pre.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("de", {
                highlight: false,
                focused: true,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Undo 2 removed the "f" from the first pre and un-highlighted it.` }
    );
    testSelectionInTextarea(editor, textarea1, "de", 2);
    // UNDO action 1: insert "l" in second pre.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("de", {
                highlight: false,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jk", {
                highlight: false,
                focused: true,
                preStyle,
            }),
        { message: `Undo 1 removed the "l" from the second pre and un-highlighted it.` }
    );
    testSelectionInTextarea(editor, textarea2, "jk", 2);
    // UNDO nothing.
    await press(["ctrl", "z"]);
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("de", {
                highlight: false,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jk", {
                highlight: false,
                focused: true,
                preStyle,
            }),
        { message: "Undo did nothing." }
    );
    testSelectionInTextarea(editor, textarea2, "jk", 2);

    // REDO
    // ----

    // REDO action 1: insert "l" in second pre.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("de", {
                highlight: false,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                focused: true,
                preStyle,
            }),
        { message: `Redo 1 reinserted "l" into the second pre and re-highlighted it.` }
    );
    testSelectionInTextarea(editor, textarea2, "jkl", 3);
    // REDO action 2: insert "f" in first pre.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>ab</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                focused: true,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Redo 2 reinserted "f" into the first pre and re-highlighted it.` }
    );
    testSelectionInTextarea(editor, textarea1, "def", 3);
    // REDO action 3: insert "c" in first paragraph.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>abc[]</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
            }) +
            "<p>gh</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Redo 3 reinserted "c" into the first paragraph.` }
    );
    // REDO action 4: insert "i" in second paragraph.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                highlight: true,
                preStyle,
            }) +
            "<p>ghi[]</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Redo 4 reinserted "i" into the second paragraph.` }
    );
    // REDO action 5: change the language of first textarea.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                language: "javascript",
                highlight: true,
                focused: true,
                preStyle,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                highlight: true,
                preStyle,
            }),
        { message: `Redo 5 changed back the language of the first textarea to "javascript".` }
    );
    // REDO action 6: change the language of second textarea.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                language: "javascript",
                highlight: true,
                preStyle,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                language: "python",
                highlight: true,
                focused: true,
                preStyle,
            }),
        { message: `Redo 6 changed back the language of the second textarea to "python".` }
    );
    // REDO nothing.
    await press(["ctrl", "y"]);
    expect(getContent(el)).toBe(
        "<p>abc</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("def", {
                language: "javascript",
                highlight: true,
                preStyle,
            }) +
            "<p>ghi</p>" +
            SYNTAX_HIGHLIGHTING_WRAPPER("jkl", {
                language: "python",
                highlight: true,
                focused: true,
                preStyle,
            }),
        { message: "Redo did nothing." }
    );
});

test("can copy content with the copy button", async () => {
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });
    const { editor } = await setupEditor("<pre>abc</pre>");
    const textarea = queryOne("textarea");
    await click(textarea);
    testSelectionInTextarea(editor, textarea, "abc", 3);
    await animationFrame();
    await waitFor(".o_code_toolbar");
    // Copy "abc".
    await click(".o_code_toolbar .o_clipboard_button");
    expect.verifySteps(["abc"]);
    // Change text.
    await click(textarea);
    testSelectionInTextarea(editor, textarea, "abc", 3);
    await press("d");
    testSelectionInTextarea(editor, textarea, "abcd", 4);
    // Copy "abcd"
    await click(".o_code_toolbar .o_clipboard_button");
    expect.verifySteps(["abcd"]);
});
