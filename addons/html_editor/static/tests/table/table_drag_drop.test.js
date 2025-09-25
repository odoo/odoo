import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { expectElementCount } from "../_helpers/ui_expectations";
import { hover, manuallyDispatchProgrammaticEvent, waitFor } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";
import { redo, undo } from "../_helpers/user_actions";
import { delay } from "@web/core/utils/concurrency";

test("should move first column after second column on drag and drop", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                    </tr>
                    <tr>
                        <td class="d">4</td>
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over first cell to trigger column menu
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");
    const colMenu = document.querySelector("[data-type='column'].o-we-table-menu");
    const colMenuRect = colMenu.getBoundingClientRect();
    // Start long press on column menu
    await manuallyDispatchProgrammaticEvent(colMenu, "pointerdown", {
        clientX: colMenuRect.x + colMenuRect.width / 2,
        clientY: colMenuRect.y,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    const targetCell = el.querySelector("td.b");
    const targetCellRect = targetCell.getBoundingClientRect();
    // Drag overlay to the right of second column
    await manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b td-highlight-right">2</td>
                        <td class="c">3</td>
                    </tr>
                    <tr>
                        <td class="d">4</td>
                        <td class="e td-highlight-right">5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Release pointer to drop the first column after the second column.
    await manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    await expectElementCount(".o-we-table-drag-drop", 0);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="b">2</td>
                        <td class="a">[]1</td>
                        <td class="c">3</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                        <td class="d">4</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should move third column before first column on drag and drop", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">1</td>
                        <td class="b">2</td>
                        <td class="c">[]3</td>
                    </tr>
                    <tr>
                        <td class="d">4</td>
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over third column header cell to trigger column menu
    await hover(el.querySelector("td.c"));
    await waitFor("[data-type='column'].o-we-table-menu");
    const colMenu = document.querySelector("[data-type='column'].o-we-table-menu");
    const colMenuRect = colMenu.getBoundingClientRect();
    // Start long press drag on third column
    await manuallyDispatchProgrammaticEvent(colMenu, "pointerdown", {
        clientX: colMenuRect.x + colMenuRect.width / 2,
        clientY: colMenuRect.y,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    const targetCell = el.querySelector("td.a");
    const targetCellRect = targetCell.getBoundingClientRect();
    // Drag overlay to the left of first column
    await manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: targetCellRect.x - targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a td-highlight-left">1</td>
                        <td class="b">2</td>
                        <td class="c">[]3</td>
                    </tr>
                    <tr>
                        <td class="d td-highlight-left">4</td>
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Release pointer to drop the third column before the first column
    await manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
        clientX: targetCellRect.x - targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    await expectElementCount(".o-we-table-drag-drop", 0);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="c">[]3</td>
                        <td class="a">1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td class="f">6</td>
                        <td class="d">4</td>
                        <td class="e">5</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("undo/redo should work correctly after dragging and dropping a column", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over first cell to trigger column menu
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");
    const colMenu = document.querySelector("[data-type='column'].o-we-table-menu");
    const colMenuRect = colMenu.getBoundingClientRect();
    // Start long press drag on first column
    await manuallyDispatchProgrammaticEvent(colMenu, "pointerdown", {
        clientX: colMenuRect.x + colMenuRect.width / 2,
        clientY: colMenuRect.y,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    const targetCell = el.querySelector("td.c");
    const targetCellRect = targetCell.getBoundingClientRect();
    // Drag overlay to the right of last column
    await manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    // Release pointer to drop the first column after the third column
    await manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    await expectElementCount(".o-we-table-drag-drop", 0);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="a">[]1</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Undo the drag and drop
    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Redo the drag and drop
    redo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="a">[]1</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should move first header row to last position on drag and drop", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <th class="a o_table_header">[]1</th>
                        <th class="b o_table_header">2</th>
                    </tr>
                    <tr>
                        <td class="c">3</td>
                        <td class="d">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over the first row to trigger row menu
    await hover(el.querySelector("th.a"));
    await waitFor("[data-type='row'].o-we-table-menu");
    const rowMenu = document.querySelector("[data-type='row'].o-we-table-menu");
    const rowMenuRect = rowMenu.getBoundingClientRect();
    // Start long press drag on first header row
    await manuallyDispatchProgrammaticEvent(rowMenu, "pointerdown", {
        clientX: rowMenuRect.x,
        clientY: rowMenuRect.y + rowMenuRect.height / 2,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    const targetRow = el.querySelector("tr:last-child");
    const targetRowRect = targetRow.getBoundingClientRect();
    // Drag overlay to the position of last row
    await manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <th class="a o_table_header">[]1</th>
                        <th class="b o_table_header">2</th>
                    </tr>
                    <tr>
                        <td class="c">3</td>
                        <td class="d">4</td>
                    </tr>
                    <tr class="tr-highlight-bottom">
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Release pointer to drop the first row at last position
    await manuallyDispatchProgrammaticEvent(targetRow, "pointerup", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });
    await expectElementCount(".o-we-table-drag-drop", 0);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <th class="o_table_header">3</th>
                        <th class="o_table_header">4</th>
                    </tr>
                    <tr class="">
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                    <tr>
                        <td>[]1</td>
                        <td>2</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should move last row above the first header row on drag and drop", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <th class="a o_table_header">1</th>
                        <th class="b o_table_header">2</th>
                    </tr>
                    <tr>
                        <td class="c">3</td>
                        <td class="d">4</td>
                    </tr>
                    <tr>
                        <td class="e">[]5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over the last row to trigger row menu
    await hover(el.querySelector("td.e"));
    await waitFor("[data-type='row'].o-we-table-menu");
    const rowMenu = document.querySelector("[data-type='row'].o-we-table-menu");
    const rowMenuRect = rowMenu.getBoundingClientRect();
    // Start long press drag on the last row
    await manuallyDispatchProgrammaticEvent(rowMenu, "pointerdown", {
        clientX: rowMenuRect.x,
        clientY: rowMenuRect.y + rowMenuRect.height / 2,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    const targetRow = el.querySelector("tr:first-child"); // first header row
    const targetRowRect = targetRow.getBoundingClientRect();
    // Drag overlay above the first header row
    await manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y - targetRowRect.height * 0.75,
    });
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr class="tr-highlight-top">
                        <th class="a o_table_header">1</th>
                        <th class="b o_table_header">2</th>
                    </tr>
                    <tr>
                        <td class="c">3</td>
                        <td class="d">4</td>
                    </tr>
                    <tr>
                        <td class="e">[]5</td>
                        <td class="f">6</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Release pointer to drop the last row above the header row
    await manuallyDispatchProgrammaticEvent(targetRow, "pointerup", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y - targetRowRect.height * 0.75,
    });
    await expectElementCount(".o-we-table-drag-drop", 0);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <th class="o_table_header">[]5</th>
                        <th class="o_table_header">6</th>
                    </tr>
                    <tr class="">
                        <td>1</td>
                        <td>2</td>
                    </tr>
                    <tr>
                        <td class="c">3</td>
                        <td class="d">4</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("undo/redo should work correctly after dragging and dropping a row", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td class="a">[]1</td></tr>
                    <tr><td class="b">2</td></tr>
                    <tr><td class="c">3</td></tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over the first row to trigger the row menu
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");
    const rowMenu = document.querySelector("[data-type='row'].o-we-table-menu");
    const rowMenuRect = rowMenu.getBoundingClientRect();
    // Start long press drag on the first row
    await manuallyDispatchProgrammaticEvent(rowMenu, "pointerdown", {
        clientX: rowMenuRect.x,
        clientY: rowMenuRect.y + rowMenuRect.height / 2,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    const targetRow = el.querySelector("tr:last-child"); // Drop position (last row)
    const targetRowRect = targetRow.getBoundingClientRect();
    // Drag overlay to the position of the last row
    await manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });
    // Release pointer to drop the first row at last position
    await manuallyDispatchProgrammaticEvent(targetRow, "pointerup", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });
    await expectElementCount(".o-we-table-drag-drop", 0);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td class="b">2</td></tr>
                    <tr class=""><td class="c">3</td></tr>
                    <tr><td class="a">[]1</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Undo the drag and drop
    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td class="a">[]1</td></tr>
                    <tr><td class="b">2</td></tr>
                    <tr><td class="c">3</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Redo the drag and drop
    redo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td class="b">2</td></tr>
                    <tr><td class="c">3</td></tr>
                    <tr><td class="a">[]1</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});
