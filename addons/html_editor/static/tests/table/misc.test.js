import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import {
    advanceTime,
    click,
    manuallyDispatchProgrammaticEvent,
    queryAll,
    queryFirst,
    queryOne,
    waitFor,
} from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { getContent, setSelection, waitForSelectionChange } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";
import { expandToolbar } from "../_helpers/toolbar";
import { expectElementCount } from "../_helpers/ui_expectations";
import { deleteBackward, getElementTouchPosition } from "../_helpers/user_actions";
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
        expect("[data-icon='colors']").toHaveCount(1);
        expect("[data-icon='colors']").toHaveStyle({
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
        expect("[data-icon='colors']").toHaveCount(1);
        expect("[data-icon='colors']").toHaveStyle({
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
        expect("[data-icon='colors']").toHaveCount(1);
        expect("[data-icon='colors']").toHaveStyle({
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
        expect("[data-icon='colors']").toHaveCount(1);
        expect("[data-icon='colors']").toHaveStyle({
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
        expect("[data-icon='colors']").toHaveCount(1);
        expect("[data-icon='colors']").toHaveStyle({
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
        expect("[data-icon='colors']").toHaveCount(1);
        expect("[data-icon='colors']").toHaveStyle({
            "border-bottom": "2px solid rgba(255, 0, 0, 0.6)",
        });
    });
});

describe("normalize table structure", () => {
    test("should create a tbody when it's missing", async () => {
        const { el, editor } = await setupEditor(
            `<table class="table table-bordered o_table" style="width: 500px;"><caption>c</caption></table>`
        );
        expect(editor.isDestroyed).toBe(false);
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table" style="width: 500px;">
                    <caption>c</caption>
                    <tbody>
                        <tr>
                            <td><div class="o-paragraph"><br></div></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
            `)
        );
    });

    test("should convert thead to tbody", async () => {
        const { el } = await setupEditor(
            `<table style="width: 500px;"><thead><tr><th>1</th><th>2</th></tr></thead></table>`
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table style="width: 500px;">
                    <tbody>
                        <tr>
                            <th class="o_table_header">1</th>
                            <th class="o_table_header">2</th>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder=""><br></p>
            `)
        );
    });

    test("should move thead rows into the existing tbody", async () => {
        const { el } = await setupEditor(
            unformat(
                `<table style="width: 500px;">
                    <thead><tr><th>1</th><th>2</th></tr></thead>
                    <tbody><tr><td>3</td><td>4</td></tr></tbody>
                </table>`
            )
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table style="width: 500px;">
                    <tbody>
                        <tr>
                            <th class="o_table_header">1</th>
                            <th class="o_table_header">2</th>
                        </tr>
                        <tr>
                            <td>3</td>
                            <td>4</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder=""><br></p>
            `)
        );
    });
});

describe("Table merge/unmerge button visibility", () => {
    test("shouldn't show merge button in toolbar when selection spans multiple rows and columns", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="b"><p><br></p></td>
                            <td><p><br>]</p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td class="o_selected_td"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="b o_selected_td"><p><br></p></td>
                            <td class="o_selected_td"><p><br>]</p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 0);
    });

    test("shouldn't show merge button in toolbar when selection includes cells with rowspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td rowspan="2"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a">[<p><br></p></td>
                            <td><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td rowspan="2" class="o_selected_td"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td">[<p><br></p></td>
                            <td class="o_selected_td"><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 0);
    });
    test("shouldn't show merge button in toolbar when selection includes cells with colspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td colspan="3"><p>]<br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td colspan="3" class="o_selected_td"><p>]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 0);
    });

    test("should show inactive merge button in toolbar when selection includes cells in a single row including a merged cell", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a" rowspan="2"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br>]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="o_selected_td"><p><br>]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']:not(.active)", 1);
    });

    test("should show inactive merge button in toolbar when selection includes cells in a single column including a merged cell", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a" colspan="2"><p>[<br></p></td>
                            <td><p><br>]</p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="2"><p>[<br></p></td>
                            <td class="o_selected_td"><p><br>]</p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']:not(.active)", 1);
    });

    test("should show active merge button in toolbar when selecting a merged row cell", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p>[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells'].active", 1);
    });

    test("should show active merge button in toolbar when selecting a merged column cell", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p>[]<br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells'].active", 1);
    });
});

describe("Merge column cells", () => {
    test("merges selected cells in a single row into one with colspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a">[<p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td">[<p><br></p></td>
                            <td class="o_selected_td"><p><br></p></td>
                            <td class="o_selected_td"><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test("merges selected filled cells by combining their content into one cell with colspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a">[<p>a</p></td>
                            <td><p>b</p></td>
                            <td><p>c</p>]</td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td">[<p>a</p></td>
                            <td class="o_selected_td"><p>b</p></td>
                            <td class="o_selected_td"><p>c</p>]</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p>[a</p><p>b</p><p>c]</p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test.tags("mobile");
    test("merges selected cells in a single row into one with colspan (mobile)", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p><br></p></td>
                            <td><p><br></p></td>
                            <td class="b"><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );

        await manuallyDispatchProgrammaticEvent(queryOne("td.b"), "touchstart", {
            touches: [getElementTouchPosition("td.b")],
        });
        await advanceTime(200);
        await manuallyDispatchProgrammaticEvent(queryOne("td.a"), "touchmove", {
            touches: [getElementTouchPosition("td.a")],
        });
        await manuallyDispatchProgrammaticEvent(queryOne("td.a"), "touchend", {
            touches: [getElementTouchPosition("td.a")],
        });

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
});

describe("Merge row cells", () => {
    test("merges selected cells vertically in a column by applying rowspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br>]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="o_selected_td"><p><br>]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test("merges filled cells vertically by combining their content into one cell with rowspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[a</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p>b]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[a</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="o_selected_td"><p>b]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p>[a</p><p>b]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test("does not display merge cell option when selecting multiple cells from different tables", async () => {
        const { el } = await setupEditor(
            unformat(`
                <p><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br>]</p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="o_selected_td"><p><br>]</p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 0);
    });

    test.tags("mobile");
    test("merges selected cells in a single column into one with rowspan (mobile)", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td class="a"><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td class="b"><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );

        await manuallyDispatchProgrammaticEvent(queryOne("td.b"), "touchstart", {
            touches: [getElementTouchPosition("td.b")],
        });
        await advanceTime(200);
        await manuallyDispatchProgrammaticEvent(queryOne("td.a"), "touchmove", {
            touches: [getElementTouchPosition("td.a")],
        });
        await manuallyDispatchProgrammaticEvent(queryOne("td.a"), "touchend", {
            touches: [getElementTouchPosition("td.a")],
        });

        await expandToolbar();
        await expectElementCount("button[name='mergeCells']", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td class="a o_selected_td" rowspan="3"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
});

describe("unmerge cells option", () => {
    test("unmerge merged row cells via toolbar", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p>[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells'].active", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
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
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
    test("unmerge merged column cells via toolbar", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p>[]<br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells'].active", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
    test("unmerge merged filled row cells via toolbar", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p>a[]</p><p>b</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells'].active", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>a[]</p><p>b</p></td>
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
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
    test("unmerge merged filled column cells via toolbar", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p>a[]</p><p>b</p></td>
                        </tr>
                    </tbody>
                </table>`)
        );

        await expandToolbar();
        await expectElementCount("button[name='mergeCells'].active", 1);
        await click("button[name='mergeCells']");

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td"><p>a[]</p><p>b</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
});
