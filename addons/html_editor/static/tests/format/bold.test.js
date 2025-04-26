import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { BOLD_TAGS, notStrong, span, strong, em } from "../_helpers/tags";
import { bold, italic, simulateArrowKeyPress, tripleClick } from "../_helpers/user_actions";

const styleH1Bold = `h1 { font-weight: bold; }`;

test("should make a few characters bold", async () => {
    await testEditor({
        contentBefore: "<p>ab[cde]fg</p>",
        stepFunction: bold,
        contentAfter: `<p>ab${strong(`[cde]`)}fg</p>`,
    });
});

test("should make a few characters not bold", async () => {
    await testEditor({
        contentBefore: `<p>${strong(`ab[cde]fg`)}</p>`,
        stepFunction: bold,
        contentAfter: `<p>${strong(`ab`)}[cde]${strong(`fg`)}</p>`,
    });
});

test("should make two paragraphs bold", async () => {
    await testEditor({
        contentBefore: "<p>[abc</p><p>def]</p>",
        stepFunction: bold,
        contentAfter: `<p>${strong(`[abc`)}</p><p>${strong(`def]`)}</p>`,
    });
});

test("should make two paragraphs not bold", async () => {
    await testEditor({
        contentBefore: `<p>${strong(`[abc`)}</p><p>${strong(`def]`)}</p>`,
        stepFunction: bold,
        contentAfter: `<p>[abc</p><p>def]</p>`,
    });
});

test("should make qweb tag bold", async () => {
    await testEditor({
        contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: bold,
        contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="font-weight: bolder;">Test</p>]</div>`,
    });
    await testEditor({
        contentBefore: `<div><p t-field="record.name" contenteditable="false">[Test]</p></div>`,
        stepFunction: bold,
        contentAfter: `<div>[<p t-field="record.name" contenteditable="false" style="font-weight: bolder;">Test</p>]</div>`,
    });
});

test("should make qweb tag bold and create a step even with partial selection inside contenteditable false", async () => {
    const { editor, el } = await setupEditor(
        `<div><p t-esc="'Test'" contenteditable="false">T[e]st</p></div>`
    );
    bold(editor);
    expect(getContent(el)).toBe(
        `<div>[<p t-esc="'Test'" contenteditable="false" style="font-weight: bolder;">Test</p>]</div>`
    );
    expect(queryOne(`p[contenteditable="false"]`).childNodes.length).toBe(1);
    const historySteps = editor.shared.history.getHistorySteps();
    expect(historySteps.length).toBe(2);
    const lastStep = historySteps.at(-1);
    expect(lastStep.mutations.length).toBe(1);
    expect(lastStep.mutations[0].type).toBe("attributes");
    expect(lastStep.mutations[0].attributeName).toBe("style");
    expect(lastStep.mutations[0].value).toBe("font-weight: bolder;");
});

test("should make a whole heading bold after a triple click", async () => {
    await testEditor({
        styleContent: styleH1Bold,
        contentBefore: `<h1>${notStrong(`[ab`)}</h1><p>]cd</p>`,
        stepFunction: bold,
        contentAfter: `<h1>[ab]</h1><p>cd</p>`,
    });
});

test("should make a whole heading not bold after a triple click (heading is considered bold)", async () => {
    const { el, editor } = await setupEditor(`<h1>[ab</h1><p>]cd</p>`, {
        styleContent: styleH1Bold,
    });
    await tripleClick(el.querySelector("h1"));
    bold(editor);
    expect(getContent(el)).toBe(`<h1>${notStrong(`[ab]`)}</h1><p>cd</p>`);
});

test("should make a selection starting with bold text fully bold", async () => {
    await testEditor({
        contentBefore: `<p>${strong(`[ab`)}</p><p>c]d</p>`,
        stepFunction: bold,
        contentAfter: `<p>${strong(`[ab`)}</p><p>${strong(`c]`)}d</p>`,
    });
});

test("should make a selection with bold text in the middle fully bold", async () => {
    await testEditor({
        contentBefore: `<p>[a${strong(`b`)}</p><p>${strong(`c`)}d]e</p>`,
        stepFunction: bold,
        contentAfter: `<p>${strong(`[ab`)}</p><p>${strong(`cd]`)}e</p>`,
    });
});

test("should make a selection ending with bold text fully bold", async () => {
    await testEditor({
        styleContent: styleH1Bold,
        contentBefore: `<h1>${notStrong(`[ab`)}</h1><p>${strong(`c]d`)}</p>`,
        stepFunction: bold,
        contentAfter: `<h1>[ab</h1><p>${strong(`c]d`)}</p>`,
    });
});

test("should get ready to type in bold", async () => {
    await testEditor({
        contentBefore: "<p>ab[]cd</p>",
        stepFunction: bold,
        contentAfterEdit: `<p>ab${strong(`[]\u200B`, "first")}cd</p>`,
        contentAfter: `<p>ab[]cd</p>`,
    });
});

test("should get ready to type in not bold", async () => {
    await testEditor({
        contentBefore: `<p>${strong(`ab[]cd`)}</p>`,
        stepFunction: bold,
        contentAfterEdit: `<p>${strong(`ab`)}${span(`[]\u200B`, "first")}${strong(`cd`)}</p>`,
        contentAfter: `<p>${strong(`ab[]cd`)}</p>`,
    });
});

test("should remove a bold tag that was redondant while performing the command", async () => {
    for (const tag of BOLD_TAGS) {
        await testEditor({
            contentBefore: `<p>a${tag(`b${tag(`[c]`)}d`)}e</p>`,
            stepFunction: bold,
            contentAfter: `<p>a${tag("b")}[c]${tag("d")}e</p>`,
        });
    }
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
        contentAfter: `<p>${strong("[a")}</p><p contenteditable="false">b</p><p>${strong(
            "c]"
        )}</p>`,
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
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p>${strong(`[abc`)}</p></td>
                        <td class="o_selected_td"><p>${strong(`def`)}</p></td>
                        <td class="o_selected_td"><p>${strong(`]<br>`)}</p></td>
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
    });
});

test("should insert a span zws when toggling a formatting command twice", () => {
    return testEditor({
        contentBefore: `<p>[]<br></p>`,
        stepFunction: async (editor) => {
            bold(editor);
            bold(editor);
        },
        // todo: It would be better to remove the zws entirely so that
        // the P could have the "/" hint but that behavior might be
        // complex with the current implementation.
        contentAfterEdit: `<p>${span(`[]\u200B`, "first")}</p>`,
    });
});

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
    expect(getContent(el)).toBe(`<p>ab${strong("[]\u200B", "first")}cd</p>`);

    // Simulate text insertion as done by the contenteditable.
    await typeChar(editor, "x");
    // Check that character was inserted inside the strong tag.
    expect(getContent(el)).toBe(`<p>ab${strong("x[]")}cd</p>`);

    // Keep typing.
    await typeChar(editor, "y");
    expect(getContent(el)).toBe(`<p>ab${strong("xy[]")}cd</p>`);

    // Toggle bold off and type more.
    bold(editor);
    expect(getContent(el)).toBe(`<p>ab${strong("xy")}${span("[]\u200B", "first")}cd</p>`);
    await typeChar(editor, "z");
    expect(getContent(el)).toBe(`<p>ab${strong("xy")}z[]cd</p>`);
});

test.tags("desktop");
test("create bold with shortcut + selected with arrow", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");
    await press(["control", "b"]);
    expect(getContent(el)).toBe(`<p>ab${strong("[]\u200B", "first")}cd</p>`);

    await simulateArrowKeyPress(editor, ["Shift", "ArrowRight"]);
    await tick(); // await selectionchange
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1);
    expect(getContent(el)).toBe(`<p>ab${strong("[\u200B", "first")}c]d</p>`);

    await simulateArrowKeyPress(editor, ["Shift", "ArrowLeft"]);
    await tick(); // await selectionchange
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(0);
    expect(getContent(el)).toBe(`<p>ab${strong("[\u200B]", "first")}cd</p>`);
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

    test("should force the font-weight to normal while removing redundant tag", async () => {
        for (const tag of BOLD_TAGS) {
            await testEditor({
                styleContent: styleContentBold,
                contentBefore: `<p class="boldClass">a${tag("[b]")}c</p>`,
                stepFunction: bold,
                contentAfter: `<p class="boldClass">a<span style="font-weight: normal;">[b]</span>c</p>`,
            });
        }
    });
});

describe("inside container font-weight: 500 and strong being strong-weight: 500", () => {
    test("should remove the redundant strong style and add span with a bolder font-weight", async () => {
        await testEditor({
            styleContent: `h1, strong {font-weight: 500;}`,
            contentBefore: `<h1>a${strong(`[b]`)}c</h1>`,
            stepFunction: bold,
            contentAfter: `<h1>a<span style="font-weight: bolder;">[b]</span>c</h1>`,
        });
    });
});

test("should remove empty bold tag when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");

    bold(editor);
    await tick();
    expect(getContent(el)).toBe(`<p>ab${strong("[]\u200B", "first")}cd</p>`);

    await simulateArrowKeyPress(editor, "ArrowLeft");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>a[]bcd</p>`);
});

test("should remove multiple formatted empty bold tag when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");

    bold(editor);
    italic(editor);
    await tick();
    expect(getContent(el)).toBe(`<p>ab${strong(em("[]\u200B", "first"), "first")}cd</p>`);

    await simulateArrowKeyPress(editor, "ArrowLeft");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>a[]bcd</p>`);
});

test("should not remove empty bold tag in an empty block when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>abcd</p><p>[]<br></p>");

    bold(editor);
    await tick();
    expect(getContent(el)).toBe(`<p>abcd</p><p>${strong("[]\u200B", "first")}</p>`);

    await simulateArrowKeyPress(editor, "ArrowUp");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>[]abcd</p><p>${strong("\u200B", "first")}</p>`);
});
