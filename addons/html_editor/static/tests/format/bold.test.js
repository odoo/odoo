import { describe, expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { expectElementCount } from "../_helpers/ui_expectations";
import {
    bold,
    insertText,
    italic,
    simulateArrowKeyPress,
    tripleClick,
    undo,
} from "../_helpers/user_actions";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { EDITOR_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";

const styleH1Bold = `h1 { font-weight: bold; }`;

test("should make a few characters bold", async () => {
    await testEditor({
        contentBefore: "<p>ab[cde]fg</p>",
        stepFunction: bold,
        contentAfter: `<p>ab<strong>[cde]</strong>fg</p>`,
    });
});

test("should make a few characters not bold", async () => {
    await testEditor({
        contentBefore: `<p><strong>ab[cde]fg</strong></p>`,
        stepFunction: bold,
        contentAfter: `<p><strong>ab</strong>[cde]<strong>fg</strong></p>`,
    });
});

test("should make two paragraphs bold", async () => {
    await testEditor({
        contentBefore: "<p>[abc</p><p>def]</p>",
        stepFunction: bold,
        contentAfter: `<p><strong>[abc</strong></p><p><strong>def]</strong></p>`,
    });
});

test("should make two paragraphs not bold", async () => {
    await testEditor({
        contentBefore: `<p><strong>[abc</strong></p><p><strong>def]</strong></p>`,
        stepFunction: bold,
        contentAfter: `<p>[abc</p><p>def]</p>`,
    });
});

test("should make qweb tag bold (1)", async () => {
    await testEditor({
        contentBefore: `<div><p t-out="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: bold,
        contentAfter: `<div>[<p t-out="'Test'" style="font-weight: bolder;">Test</p>]</div>`,
        config: { Plugins: [...MAIN_PLUGINS, QWebPlugin] },
    });
});

test("should make qweb tag bold (2)", async () => {
    await testEditor({
        contentBefore: `<div><p t-field="record.name" contenteditable="false">[Test]</p></div>`,
        stepFunction: bold,
        contentAfter: `<div>[<p t-field="record.name" style="font-weight: bolder;">Test</p>]</div>`,
        config: { Plugins: [...MAIN_PLUGINS, QWebPlugin] },
    });
});

test("should make qweb tag bold and create a commit even with partial selection inside contenteditable false", async () => {
    const { editor, el } = await setupEditor(
        `<div><p t-out="'Test'" contenteditable="false">T[e]st</p></div>`,
        { config: { Plugins: [...MAIN_PLUGINS, QWebPlugin] } }
    );
    bold(editor);
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder=""><br></p>' +
            `<div>[<p t-out="'Test'" contenteditable="false" data-oe-protected="true" style="font-weight: bolder;">Test</p>]</div>` +
            '<p data-selection-placeholder=""><br></p>'
    );
    expect(queryOne(`p[contenteditable="false"]`).childNodes.length).toBe(1);
    const historyCommits = editor.shared.history.getCommits();
    expect(historyCommits.length).toBe(2);
    const lastCommit = historyCommits.at(-1);
    expect(lastCommit.data.mutations.length).toBe(1);
    expect(lastCommit.data.mutations[0].type).toBe(EDITOR_MUTATION_TYPES.ATTRIBUTES);
    expect(lastCommit.data.mutations[0].attributeName).toBe("style");
    expect(lastCommit.data.mutations[0].value).toBe("font-weight: bolder;");
});

test("bold is active when the selection wraps a bold qweb node", async () => {
    await setupEditor(`<p>[<strong t-out="'Test'" contenteditable="false">Test</strong>]</p>`, {
        config: { Plugins: [...MAIN_PLUGINS, QWebPlugin] },
    });
    await animationFrame();
    await expectElementCount('.o-we-toolbar [name="bold"].active', 1);
});

test("bold is inactive when the selection contains a non-bold qweb node", async () => {
    await setupEditor(
        `<p>[<span t-out="'Test'" contenteditable="false">Test</span><strong>Y]</strong></p>`,
        { config: { Plugins: [...MAIN_PLUGINS, QWebPlugin] } }
    );
    await animationFrame();
    await expectElementCount('.o-we-toolbar [name="bold"]:not(.active)', 1);
});

test.tags("desktop");
test("should make a whole heading bold after a triple click", async () => {
    await testEditor({
        styleContent: styleH1Bold,
        contentBefore: `<h1><span style="font-weight: normal;">ab</span></h1><p>cd</p>`,
        stepFunction: async (editor) => {
            await tripleClick(editor.editable.querySelector("h1"));
            bold(editor);
        },
        contentAfter: `<h1>[ab]</h1><p>cd</p>`,
    });
});

test.tags("desktop");
test("should make a whole heading not bold after a triple click (heading is considered bold)", async () => {
    const { el, editor } = await setupEditor(`<h1>ab</h1><p>cd</p>`, {
        styleContent: styleH1Bold,
    });
    await tripleClick(el.querySelector("h1"));
    bold(editor);
    expect(getContent(el)).toBe(`<h1 style="font-weight: normal;">[ab]</h1><p>cd</p>`);
});

test("should make a selection starting with bold text fully bold", async () => {
    await testEditor({
        contentBefore: `<p><strong>[ab</strong></p><p>c]d</p>`,
        stepFunction: bold,
        contentAfter: `<p><strong>[ab</strong></p><p><strong>c]</strong>d</p>`,
    });
});

test("should make a selection with bold text in the middle fully bold", async () => {
    await testEditor({
        contentBefore: `<p>[a<strong>b</strong></p><p><strong>c</strong>d]e</p>`,
        stepFunction: bold,
        contentAfter: `<p><strong>[ab</strong></p><p><strong>cd]</strong>e</p>`,
    });
});

test("should make a selection ending with bold text fully bold", async () => {
    await testEditor({
        styleContent: styleH1Bold,
        contentBefore: `<h1><span style="font-weight: normal;">[ab</span></h1><p><strong>c]d</strong></p>`,
        stepFunction: bold,
        contentAfter: `<h1>[ab</h1><p><strong>c]d</strong></p>`,
    });
});

describe("Redundant bold tags", () => {
    test(`should remove a strong tag that was redundant while performing the command.`, async () => {
        await testEditor({
            contentBefore: `<p>a<strong>b[c]d</strong>e</p>`,
            stepFunction: bold,
            contentAfter: `<p>a<strong>b</strong>[c]<strong>d</strong>e</p>`,
        });
    });

    test(`should remove a span tag with bold style that was redundant while performing the command.`, async () => {
        await testEditor({
            contentBefore: `<p>a<span style="font-weight: bolder;">b[c]d</span>e</p>`,
            stepFunction: bold,
            contentAfter: `<p>a<span style="font-weight: bolder;">b</span>[c]<span style="font-weight: bolder;">d</span>e</p>`,
        });
    });

    test(`should remove a b tag that was redundant while performing the command.`, async () => {
        await testEditor({
            contentBefore: `<p>a<b>b[c]d</b>e</p>`,
            stepFunction: bold,
            contentAfter: `<p>a<b>b</b>[c]<b>d</b>e</p>`,
        });
    });
});

test("should remove a bold tag that was redondant with different tags while performing the command", async () => {
    await testEditor({
        contentBefore: unformat(`<p>
                a
                <span style="font-weight: bolder;">
                    b
                    <strong>c<b>[d]</b>e</strong>
                    f
                </span>
                g
            </p>`),
        stepFunction: bold,
        contentAfter: unformat(`<p>
                a
                <span style="font-weight: bolder;">b<strong>c</strong></span>
                [d]
                <span style="font-weight: bolder;"><strong>e</strong>f</span>
                g
            </p>`),
    });
});

test("should not format non-editable text (bold)", async () => {
    await testEditor({
        contentBefore: '<p>[a</p><p contenteditable="false">b</p><p>c]</p>',
        stepFunction: bold,
        contentAfter: `<p><strong>[a</strong></p><p contenteditable="false">b</p><p><strong>c]</strong></p>`,
    });
});

test("should make a few characters bold inside table (bold)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p>[abc</p></td>
                        <td class="o_selected_td"><p>def</p></td>
                        <td class="o_selected_td"><p>]<br></p></td>
                    </tr>
                    <tr>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                </tbody>
            </table>`),
        stepFunction: bold,
        contentAfterEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p><strong>[abc</strong></p></td>
                        <td class="o_selected_td"><p><strong>def</strong></p></td>
                        <td class="o_selected_td"><p><strong>]<br></strong></p></td>
                    </tr>
                    <tr>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
            </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`),
    });
});

test("should make two paragraphs (separated with whitespace) bold", async () => {
    await testEditor({
        contentBefore: `
            <p>[abc</p>
            <p>def]</p>
        `,
        stepFunction: bold,
        contentAfter: `
            <p><strong>[abc</strong></p>
            <p><strong>def]</strong></p>
        `,
    });
});

test("should make two paragraphs (separated with whitespace) not bold", async () => {
    await testEditor({
        contentBefore: `
            <p><strong>[abc</strong></p>
            <p><strong>def]</strong></p>
        `,
        stepFunction: bold,
        contentAfter: `
            <p>[abc</p>
            <p>def]</p>
        `,
    });
});

test("should make two paragraphs (separated with whitespace) bold, then not bold", async () => {
    await testEditor({
        contentBefore: `
            <p>[abc</p>
            <p>def]</p>
        `,
        stepFunction: async (editor, { assertContentEquals }) => {
            bold(editor);
            assertContentEquals(`
            <p><strong>[abc</strong></p>
            <p><strong>def]</strong></p>
        `);
            bold(editor);
        },
        contentAfter: `
            <p>[abc</p>
            <p>def]</p>
        `,
    });
});

test("should remove bold format on formatting bold twice", () =>
    testEditor({
        contentBefore: `<p>[]<br></p>`,
        stepFunction: async (editor) => {
            bold(editor);
            bold(editor);
        },
        contentAfterEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
    }));

// This test uses execCommand to reproduce as closely as possible the browser's
// default behaviour when typing in a contenteditable=true zone.
test("should type in bold", async () => {
    async function typeChar(editor, char) {
        await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key: char });
        await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
            inputType: "insertText",
            data: char,
        });
        // Simulate text insertion as done by the contenteditable.
        editor.document.execCommand("insertText", false, char);
        // Input event is dispatched and handlers are called synchronously.
        await manuallyDispatchProgrammaticEvent(editor.editable, "keyup", { key: char });
    }

    const { editor, el } = await setupEditor("<p>ab[]cd</p>");

    /** @todo fix warnings */
    patchWithCleanup(console, { warn: () => {} });

    // Toggle bold on.
    bold(editor);
    expect(getContent(el)).toBe(`<p>ab[]cd</p>`);

    // Simulate text insertion as done by the contenteditable.
    await typeChar(editor, "x");
    // Check that character was inserted inside the strong tag.
    expect(getContent(el)).toBe(`<p>ab<strong>x[]</strong>cd</p>`);

    // Keep typing.
    await typeChar(editor, "y");
    expect(getContent(el)).toBe(`<p>ab<strong>xy[]</strong>cd</p>`);

    // Toggle bold off and type more.
    bold(editor);
    expect(getContent(el)).toBe(`<p>ab<strong>xy[]</strong>cd</p>`);
    await typeChar(editor, "z");
    expect(getContent(el)).toBe(`<p>ab<strong>xy</strong>z[]cd</p>`);
});

test.tags("desktop");
test("create bold with shortcut + selected with arrow", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");
    await press(["control", "b"]);
    expect(getContent(el)).toBe(`<p>ab[]cd</p>`);

    await simulateArrowKeyPress(editor, ["Shift", "ArrowRight"]);
    await tick(); // await selectionchange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(getContent(el)).toBe(`<p>ab[c]d</p>`);

    await simulateArrowKeyPress(editor, ["Shift", "ArrowLeft"]);
    await tick(); // await selectionchange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 0);
    expect(getContent(el)).toBe(`<p>ab[]cd</p>`);
});

const styleContentBold = `.boldClass { font-weight: bold; }`;
describe("inside container or inline with class already bold", () => {
    test("should force the font-weight to normal with an inline with class", async () => {
        await testEditor({
            styleContent: styleContentBold,
            contentBefore: `<div class="o-paragraph">a<span class="boldClass">[b]</span>c</div>`,
            stepFunction: bold,
            contentAfter: `<div>a<span class="boldClass"><span style="font-weight: normal;">[b]</span></span>c</div>`,
        });
    });

    test("should force the font-weight to normal", async () => {
        await testEditor({
            styleContent: styleContentBold,
            contentBefore: `<p class="boldClass">a[b]c</p>`,
            stepFunction: bold,
            contentAfter: `<p class="boldClass">a<span style="font-weight: normal;">[b]</span>c</p>`,
        });
    });

    test("should force the font-weight to normal while removing redundant tag. (1)", async () => {
        await testEditor({
            styleContent: styleContentBold,
            contentBefore: `<p class="boldClass">a<strong>[b]</strong>c</p>`,
            stepFunction: bold,
            contentAfter: `<p class="boldClass">a<span style="font-weight: normal;">[b]</span>c</p>`,
        });
    });

    test("should force the font-weight to normal while removing redundant tag. (2)", async () => {
        await testEditor({
            styleContent: styleContentBold,
            contentBefore: `<p class="boldClass">a<span style="font-weight: bolder;">[b]</span>c</p>`,
            stepFunction: bold,
            contentAfter: `<p class="boldClass">a<span style="font-weight: normal;">[b]</span>c</p>`,
        });
    });

    test("should force the font-weight to normal while removing redundant tag. (3)", async () => {
        await testEditor({
            styleContent: styleContentBold,
            contentBefore: `<p class="boldClass">a<b>[b]</b>c</p>`,
            stepFunction: bold,
            contentAfter: `<p class="boldClass">a<span style="font-weight: normal;">[b]</span>c</p>`,
        });
    });
});

describe("inside container font-weight: 500 and strong being strong-weight: 500", () => {
    test("should remove the redundant strong style and add span with a bolder font-weight", async () => {
        await testEditor({
            styleContent: `h1, strong {font-weight: 500;}`,
            contentBefore: `<h1>a<strong>[b]</strong>c</h1>`,
            stepFunction: bold,
            contentAfter: `<h1>a<span style="font-weight: bolder;">[b]</span>c</h1>`,
        });
    });
});

test("should remove bold state when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");

    bold(editor);
    await tick();
    expect(getContent(el)).toBe(`<p>ab[]cd</p>`);

    await simulateArrowKeyPress(editor, "ArrowLeft");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>a[]bcd</p>`);
    await insertText(editor, "x");
    expect(getContent(el)).toBe(`<p>ax[]bcd</p>`);
});

test("should remove multiple formatted state when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");

    bold(editor);
    italic(editor);
    await tick();
    expect(getContent(el)).toBe(`<p>ab[]cd</p>`);

    await simulateArrowKeyPress(editor, "ArrowLeft");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>a[]bcd</p>`);
    await insertText(editor, "x");
    expect(getContent(el)).toBe(`<p>ax[]bcd</p>`);
});

test("should not remove empty bold tag in an empty block when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>abcd</p><p>[]<br></p>");

    bold(editor);
    await tick();
    expect(getContent(el)).toBe(
        `<p>abcd</p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );

    await simulateArrowKeyPress(editor, "ArrowUp");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>[]abcd</p><p><br></p>`);
});

test("should not add history commit for bold on collapsed selection", async () => {
    const { editor, el } = await setupEditor("<p>abcd[]</p>");

    patchWithCleanup(console, { warn: () => {} });

    // Collapsed formatting shortcuts (e.g. Ctrl+B) shouldn’t create a history
    // commit. The empty inline tag is temporary: auto-cleaned if unused. We want
    // to avoid having a phantom commit in the history.
    await press(["ctrl", "b"]);
    expect(getContent(el)).toBe(`<p>abcd[]</p>`);

    await insertText(editor, "A");
    expect(getContent(el)).toBe(`<p>abcd<strong>A[]</strong></p>`);

    undo(editor);
    expect(getContent(el)).toBe(`<p>abcd[]</p>`);
});

test("Should properly apply bold format if closest element is bold but not closest block", async () => {
    const { el } = await setupEditor(
        unformat(`
            <blockquote class="blockquote">
                <em class="h4">
                    a[b]c
                </em>
            </blockquote>
        `),
        {
            styleContent: `
                blockquote {
                    font-weight: 300;   
                }
            `,
        }
    );
    await animationFrame();
    await expectElementCount('.o-we-toolbar [name="bold"].active', 1);
    await click('.o-we-toolbar [name="bold"].active');
    await animationFrame();
    expect(el).toHaveInnerHTML(
        unformat(
            `<blockquote class="blockquote">
                <em class="h4">
                    a<span style="font-weight: normal;">b</span>c
                </em>
            </blockquote>`
        )
    );
    await expectElementCount('.o-we-toolbar [name="bold"]:not(.active)', 1);
    await click('.o-we-toolbar [name="bold"]:not(.active)');
    await animationFrame();
    expect(el).toHaveInnerHTML(
        unformat(
            `<blockquote class="blockquote">
                <em class="h4">
                    abc
                </em>
            </blockquote>`
        )
    );
});

test("should not apply bold to selection placeholder nodes", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table>
                <tbody>
                    <tr>
                        <td>1[]</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await press(["ctrl", "a"]);
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder="">[<br></p>
            <table class="o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td">1</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="">]<br></p>
        `)
    );
    await press(["ctrl", "b"]);
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder="">[<br></p>
            <table class="o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><strong>1</strong></td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="">]<br></p>
        `)
    );
});

test("should not apply bold formatting for partial selection inside contenteditable false", async () => {
    const { editor, el } = await setupEditor(`<p contenteditable="false">T[e]st</p>`);
    bold(editor);
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p><p contenteditable="false">T[e]st</p><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
    );
    expect(queryOne(`p[contenteditable="false"]`).childNodes.length).toBe(1);
});

test("should toggle bold around non editable", async () => {
    const { el, editor } = await setupEditor(`<p>[a</p><p contenteditable="false">b</p><p>c]</p>`);
    bold(editor);
    expect(getContent(el)).toBe(
        `<p><strong>[a</strong></p><p contenteditable="false">b</p><p><strong>c]</strong></p>`
    );
    bold(editor);
    expect(getContent(el)).toBe(`<p>[a</p><p contenteditable="false">b</p><p>c]</p>`);
});

test("should toggle bold across indented list items", async () => {
    const { el, editor } = await setupEditor(`<ul>
        <li><strong>A[B</strong></li>
        <li>C]D</li>
    </ul>`);
    bold(editor);
    expect(getContent(el)).toBe(`<ul>
        <li><strong>A[B</strong></li>
        <li><strong>C]</strong>D</li>
    </ul>`);
    bold(editor);
    expect(getContent(el)).toBe(`<ul>
        <li><strong>A</strong>[B</li>
        <li>C]D</li>
    </ul>`);
});

test("should toggle bold across nested spans", async () => {
    const { el, editor } = await setupEditor(`<p><span><span>[A</span> </span></p><p>B]</p>`);
    bold(editor);
    expect(getContent(el)).toBe(
        `<p><span><span><strong>[A</strong></span> </span></p><p><strong>B]</strong></p>`
    );
    bold(editor);
    expect(getContent(el)).toBe(`<p><span><span>[A</span> </span></p><p>B]</p>`);
});

test("should toggle bold across sibling strongs with intervening space", async () => {
    const { el, editor } = await setupEditor(`<p><strong>[A</strong> <strong>B]</strong></p>`);
    bold(editor);
    expect(getContent(el)).toBe(`<p>[A B]</p>`);
    bold(editor);
    expect(getContent(el)).toBe(`<p><strong>[A B]</strong></p>`);
});

test("toggle bold across <strong>s with intervening unformatted word applies bold", async () => {
    await testEditor({
        contentBefore: `<p><strong>[AB</strong> CD <strong>EF]</strong></p>`,
        stepFunction: bold,
        contentAfter: `<p><strong>[AB CD EF]</strong></p>`,
    });
});

test("toggle bold on a selection that is only a formatted space", async () => {
    await testEditor({
        contentBefore: `<p>A<strong>[ ]</strong>B</p>`,
        stepFunction: bold,
        contentAfter: `<p>A[ ]B</p>`,
    });
});
