import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import {
    click,
    manuallyDispatchProgrammaticEvent,
    queryAll,
    queryFirst,
    waitFor,
} from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { getContent, setSelection, waitForSelectionChange } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";
import { expandToolbar } from "../_helpers/toolbar";
import { expectElementCount } from "../_helpers/ui_expectations";
import { deleteBackward } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";

function insertTable(editor, cols, rows) {
    execCommand(editor, "insertTable", { cols, rows });
}

describe("insertTable", () => {
    test("creates correct rows and columns", async () => {
        const { el, editor } = await setupEditor("<p>hello[]</p>", {});
        insertTable(editor, 4, 3);
        expect(el.querySelectorAll("tr")).toHaveLength(3);
        expect(el.querySelectorAll("td")).toHaveLength(12);
    });

    test("inserts table at the start", async () => {
        const { el, editor } = await setupEditor("<p>[]hello</p>", {});
        insertTable(editor, 1, 1);
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td>
                                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p>hello</p>
            `)
        );
    });

    test("inserts table in the middle", async () => {
        const { el, editor } = await setupEditor("<p>he[]llo</p>", {});
        insertTable(editor, 1, 1);
        expect(getContent(el)).toBe(
            unformat(`
                <p>he</p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td>
                                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p>llo</p>
            `)
        );
    });

    test("inserts table at the end", async () => {
        const { el, editor } = await setupEditor("<p>hello[]</p>", {});
        insertTable(editor, 1, 1);
        expect(getContent(el)).toBe(
            unformat(`
                <p>hello</p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td>
                                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
            `)
        );
    });
});

test("can color cells", async () => {
    await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td>[ab</td>
                    <td>c]</td>
                    <td>ef</td>
                </tr>
            </tbody>
        </table>`);

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0); // selector closed

    // Collapse selection to deselect cells
    setSelection({ anchorNode: queryFirst("td"), anchorOffset: 0 });
    await tick();

    const cells = queryAll("td");
    expect(cells[0]).toHaveStyle({ "background-color": "rgba(107, 173, 222, 0.6)" });
    expect(cells[1]).toHaveStyle({ "background-color": "rgba(107, 173, 222, 0.6)" });
    expect(cells[2]).not.toHaveStyle({ "background-color": "rgba(107, 173, 222, 0.6)" });
});

test("remove text from single selected cell", async () => {
    const { editor } = await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><p>[]abc</p></td>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>`);

    const firstP = queryFirst("td p");
    const { left, top } = firstP.getBoundingClientRect();
    manuallyDispatchProgrammaticEvent(firstP, "mousedown", {
        detail: 3,
        clientX: left,
        clientY: top,
    });
    await animationFrame();

    manuallyDispatchProgrammaticEvent(firstP, "mouseup", {
        detail: 3,
        clientX: left,
        clientY: top,
    });
    await animationFrame();
    deleteBackward(editor);
    expect(queryFirst("td p")).toHaveOuterHTML(
        '<p o-we-hint-text="Type &quot;/&quot; for commands" class="o-we-hint"><br></p>'
    );
});

describe("selected cell color in toolbar", () => {
    test("cell's selected color should be shown in toolbar (1)", async () => {
        await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">[ab</div></td>
                    <td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">c]</div></td>
                    <td>ef</td>
                    <td>ef</td>
                </tr>
            </tbody>
        </table>`);

        await expandToolbar();
        expect(".fa-paint-brush").toHaveCount(1);
        expect(".fa-paint-brush").toHaveStyle({
            "border-bottom": "2px solid rgba(255, 0, 0, 0.6)",
        });
    });
    test("cell's selected color should be shown in toolbar (2)", async () => {
        await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">[ab</div></td>
                    <td style="background-color: rgba(107, 173, 222, 0.6);"><div class="o-paragraph">c]</div></td>
                    <td>ef</td>
                </tr>
            </tbody>
        </table>`);

        await expandToolbar();
        await animationFrame();
        expect(".fa-paint-brush").toHaveCount(1);
        expect(".fa-paint-brush").toHaveStyle({
            "border-bottom": "2px solid rgba(0, 0, 0, 0)",
        });
    });
    test("cell's selected color should be shown in toolbar (3)", async () => {
        await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">[ab</div></td>
                    <td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">c]</div></td>
                    <td class="non_styled_1">a</td>
                    <td class="non_styled_2">c</td>
                </tr>
            </tbody>
        </table>`);

        await expandToolbar();
        expect(".fa-paint-brush").toHaveCount(1);
        expect(".fa-paint-brush").toHaveStyle({
            "border-bottom": "2px solid rgba(255, 0, 0, 0.6)",
        });
        const nonStyledCellOne = queryFirst(".non_styled_1");
        const nonStyledCellTwo = queryFirst(".non_styled_2");
        setSelection({
            anchorNode: nonStyledCellOne,
            anchorOffset: 0,
            focusNode: nonStyledCellTwo,
            focusOffset: 1,
        });
        await waitForSelectionChange();
        await animationFrame();
        expect(".fa-paint-brush").toHaveCount(1);
        expect(".fa-paint-brush").toHaveStyle({
            "border-bottom": "2px solid rgba(0, 0, 0, 0)",
        });
    });
    test("empty cell's selected color should be shown in toolbar on double click", async () => {
        const { el } = await setupEditor(`
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">[]<br></div></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`);

        const BORDER_SENSITIVITY = 5;
        const firstTd = el.querySelector("td");
        const offset = BORDER_SENSITIVITY + 1;

        manuallyDispatchProgrammaticEvent(firstTd, "mousedown", {
            detail: 2,
            clientX: offset,
            clientY: offset,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(firstTd, "mouseup", {
            detail: 2,
            clientX: offset,
            clientY: offset,
        });
        manuallyDispatchProgrammaticEvent(firstTd, "click", {
            detail: 2,
            clientX: offset,
            clientY: offset,
        });
        // the selectionchange event is usually triggered by the browser after
        // the click event, but since we are programmatically dispatching the
        // click event, we also need to manually dispatch the selectionchange
        // event to trigger the toolbar update
        manuallyDispatchProgrammaticEvent(document, "selectionchange");
        await animationFrame();

        // set a timeout for the deplayed toolbar update
        await waitFor(".o-we-toolbar", { timeout: 1500 });
        await expandToolbar();
        expect(".fa-paint-brush").toHaveCount(1);
        expect(".fa-paint-brush").toHaveStyle({
            "border-bottom": "2px solid rgba(255, 0, 0, 0.6)",
        });
    });

    test("non-empty cell's selected color should be shown in toolbar on triple click", async () => {
        const { el } = await setupEditor(`
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td style="background-color: rgba(255, 0, 0, 0.6);"><div class="o-paragraph">pp[]pp</div></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`);

        const BORDER_SENSITIVITY = 5;
        const firstTd = el.querySelector("td");
        const offset = BORDER_SENSITIVITY + 1;

        manuallyDispatchProgrammaticEvent(firstTd, "mousedown", {
            detail: 3,
            clientX: offset,
            clientY: offset,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(firstTd, "mouseup", {
            detail: 3,
            clientX: offset,
            clientY: offset,
        });
        manuallyDispatchProgrammaticEvent(firstTd, "click", {
            detail: 3,
            clientX: offset,
            clientY: offset,
        });
        await animationFrame();

        // set a timeout for the deplayed toolbar update
        await waitFor(".o-we-toolbar", { timeout: 1500 });
        await expandToolbar();
        expect(".fa-paint-brush").toHaveCount(1);
        expect(".fa-paint-brush").toHaveStyle({
            "border-bottom": "2px solid rgba(255, 0, 0, 0.6)",
        });
    });
});
