import { leftPos, rightPos } from "@html_editor/utils/position";
import { expect, test } from "@odoo/hoot";
import { animationFrame, pointerDown, pointerUp, waitForNone } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "../_helpers/editor";
import { getContent, setSelection } from "../_helpers/selection";
import { unformat } from "../_helpers/format";

/**
 * Simulates placing the cursor at the editable root after a mouse click.
 *
 * @param {HTMLElement} node
 * @param {boolean} [before=false] whether to place the cursor after the node
 */
async function simulateMouseClick(node, before = false) {
    await pointerDown(node);
    const pos = before ? leftPos(node) : rightPos(node);
    setSelection({
        anchorNode: pos[0],
        anchorOffset: pos[1],
        focusNode: pos[0],
        focusOffset: pos[1],
    });
    await tick();
    await pointerUp(node);
    await tick();
}

test("should insert a paragraph at end of editable and place cursor in it (hr)", async () => {
    await testEditor({
        contentBefore: '<hr contenteditable="false">',
        stepFunction: async (editor) => {
            const hr = editor.editable.querySelector("hr");
            await simulateMouseClick(hr);
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder="" style="margin: 8px 0px -9px;"><br></p>
            <hr contenteditable="false">
            <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        ),
        contentAfter: "<hr><p>[]<br></p>",
    });
});

test("should insert a paragraph at end of editable and place cursor in it (table)", async () => {
    await testEditor({
        contentBefore: "<table></table>",
        stepFunction: async (editor) => {
            const table = editor.editable.querySelector("table");
            await simulateMouseClick(table);
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <table></table>
            <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        ),
        contentAfter: "<table></table><p>[]<br></p>",
    });
});

test("should insert a paragraph at beginning of editable and place cursor in it (1)", async () => {
    await testEditor({
        contentBefore: '<hr contenteditable="false">',
        stepFunction: async (editor) => {
            const hr = editor.editable.querySelector("hr");
            await simulateMouseClick(hr, true);
        },
        contentAfterEdit: unformat(`
            <p data-selection-placeholder="" style="margin: 8px 0px -9px;" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
            <hr contenteditable="false">
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`),
        contentAfter: "[]<hr>",
    });
});
test("should insert a paragraph at beginning of editable and place cursor in it (2)", async () => {
    await testEditor({
        contentBefore: "<table></table>",
        stepFunction: async (editor) => {
            const table = editor.editable.querySelector("table");
            await simulateMouseClick(table, true);
        },
        contentAfterEdit: unformat(`
            <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
            <table></table>
            <p data-selection-placeholder=""><br></p>
        `),
        contentAfter: "[]<table></table>",
    });
});

test("should insert a paragraph between the two non-P blocks and place cursor in it (1)", async () => {
    await testEditor({
        contentBefore: '<hr contenteditable="false"><hr contenteditable="false">',
        stepFunction: async (editor) => {
            const firstHR = editor.editable.querySelector("hr");
            await simulateMouseClick(firstHR);
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder="" style="margin: 8px 0px -9px;"><br></p>
            <hr contenteditable="false">
            <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
            <hr contenteditable="false">
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        contentAfter: "<hr>[]<hr>",
    });
});
test("should insert a paragraph between the two non-P blocks and place cursor in it (2)", async () => {
    await testEditor({
        contentBefore: "<table></table><table></table>",
        stepFunction: async (editor) => {
            const firstTable = editor.editable.querySelector("table");
            await simulateMouseClick(firstTable);
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <table></table>
            <p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>
            <table></table>
            <p data-selection-placeholder=""><br></p>`
        ),
        contentAfter: "<table></table>[]<table></table>",
    });
});

test("should insert a paragraph before the table, then one after it", async () => {
    const { el } = await setupEditor("<table></table>");
    const table = el.querySelector("table");
    await simulateMouseClick(table, true);
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p><table></table><p data-selection-placeholder=""><br></p>`
    );
    await simulateMouseClick(table);
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p><table></table><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test.tags("desktop");
test("should have collapsed selection when mouse down on a table cell", async () => {
    const { el } = await setupEditor(
        `<table class="table table-bordered o_table"><tbody><tr><td><p><br></p></td><td><p><br>[</p></td><td><p>]<br></p></td></tr></tbody></table>`
    );
    const lastCell = el.querySelector("td:last-child");
    pointerDown(lastCell);
    await waitForNone(".o-we-toolbar");
    await animationFrame();
    const selection = document.getSelection();
    expect(selection.isCollapsed).toBe(true);
});
