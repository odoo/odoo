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

test("should not allow dropping a column inside a merged column", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="d">4</td>
                        <td class="f">5</td>
                    </tr>
                    <tr>
                        <td class="g">6</td>
                        <td colspan="3" class="h">7</td>
                        <td class="i">8</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over the first cell to display the column menu
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");
    const colMenu = document.querySelector("[data-type='column'].o-we-table-menu");
    const colMenuRect = colMenu.getBoundingClientRect();
    // Start a long press on the column menu to enable drag-and-drop
    await manuallyDispatchProgrammaticEvent(colMenu, "pointerdown", {
        clientX: colMenuRect.x + colMenuRect.width / 2,
        clientY: colMenuRect.y,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);
    // Drag to the boundary before the merged column (valid drop)
    let targetCell = el.querySelector("td.a");
    let targetCellRect = targetCell.getBoundingClientRect();

    await manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });

    // The left boundary of the merged column should highlight
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a td-highlight-right">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="d">4</td>
                        <td class="f">5</td>
                    </tr>
                    <tr>
                        <td class="g td-highlight-right">6</td>
                        <td colspan="3" class="h">7</td>
                        <td class="i">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Drag over the middle of a merged column (invalid drop position)
    targetCell = el.querySelector("td.c");
    targetCellRect = targetCell.getBoundingClientRect();
    await manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });

    // No highlight should appear on the merged column themselves.
    // Instead, the next valid boundary is highlighted
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a td-highlight-right">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="d">4</td>
                        <td class="f">5</td>
                    </tr>
                    <tr>
                        <td class="g td-highlight-right">6</td>
                        <td colspan="3" class="h">7</td>
                        <td class="i">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );

    // Drag near the right edge of the merged column (valid drop boundary)
    targetCell = el.querySelector("td.d");
    targetCellRect = targetCell.getBoundingClientRect();

    await manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: targetCellRect.x + targetCellRect.width * 0.75,
        clientY: targetCellRect.y,
    });
    // The right border of the merged column should highlight to indicate a
    // valid drop position
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="d td-highlight-right">4</td>
                        <td class="f">5</td>
                    </tr>
                    <tr>
                        <td class="g">6</td>
                        <td colspan="3" class="h td-highlight-right">7</td>
                        <td class="i">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    // Release pointer: column should be moved after the merged column
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
                        <td class="d">4</td>
                        <td class="a">[]1</td>
                        <td class="f">5</td>
                    </tr>
                    <tr>
                        <td colspan="3" class="h">7</td>
                        <td class="g">6</td>
                        <td class="i">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should not allow dragging a merged column", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                        <td class="d">4</td>
                        <td class="f">5</td>
                    </tr>
                    <tr>
                        <td class="g">6</td>
                        <td colspan="3" class="h">7</td>
                        <td class="i">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    await expectElementCount(".o-we-table-menu", 0);
    // Hover over first cell to trigger column menu
    await hover(el.querySelector("td.b"));
    await waitFor("[data-type='column'].o-we-table-menu");
    const colMenu = document.querySelector("[data-type='column'].o-we-table-menu");
    const colMenuRect = colMenu.getBoundingClientRect();
    // Start a long press on the merged column menu
    await manuallyDispatchProgrammaticEvent(colMenu, "pointerdown", {
        clientX: colMenuRect.x + colMenuRect.width / 2,
        clientY: colMenuRect.y,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    // Drag overlay should not appear for merged columns
    await expectElementCount(".o-we-table-drag-drop", 0);
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
                        <th class="c o_table_header">3</th>
                        <th class="d o_table_header">4</th>
                    </tr>
                    <tr class="">
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
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

test("should not allow dropping a row inside a merged row", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td class="d">3</td>
                        <td rowspan="3" class="c">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                    </tr>
                    <tr>
                        <td class="f">6</td>
                    </tr>
                    <tr>
                        <td class="g">7</td>
                        <td class="h">8</td>
                    </tr>
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
    // Long press to start drag
    await manuallyDispatchProgrammaticEvent(rowMenu, "pointerdown", {
        clientX: rowMenuRect.x,
        clientY: rowMenuRect.y + rowMenuRect.height / 2,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    await expectElementCount(".o-we-table-drag-drop", 1);

    // Drag over top boundary of merged row
    let targeCell = el.querySelector("td.a");
    let targetRow = targeCell.parentElement;
    let targetRowRect = targetRow.getBoundingClientRect();
    await manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });

    // Top border of merged row should highlight
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr class="tr-highlight-bottom">
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td class="d">3</td>
                        <td rowspan="3" class="c">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                    </tr>
                    <tr>
                        <td class="f">6</td>
                    </tr>
                    <tr>
                        <td class="g">7</td>
                        <td class="h">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );

    // Drag over the middle of a merged row (invalid drop position)
    targeCell = el.querySelector("td.e");
    targetRow = targeCell.parentElement;
    targetRowRect = targetRow.getBoundingClientRect();
    await manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });

    // No highlight should appear on the merged rows themselves.
    // Instead, the next valid boundary is highlighted
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr class="tr-highlight-bottom">
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td class="d">3</td>
                        <td rowspan="3" class="c">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                    </tr>
                    <tr>
                        <td class="f">6</td>
                    </tr>
                    <tr>
                        <td class="g">7</td>
                        <td class="h">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );

    // Drag just past merged row bottom
    targeCell = el.querySelector("td.f");
    targetRow = targeCell.parentElement;
    targetRowRect = targetRow.getBoundingClientRect();
    await manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
        clientX: targetRowRect.x,
        clientY: targetRowRect.y + targetRowRect.height * 0.75,
    });

    // Bottom border of merged row should highlight
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr class="">
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td class="d">3</td>
                        <td rowspan="3" class="c">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                    </tr>
                    <tr class="tr-highlight-bottom">
                        <td class="f">6</td>
                    </tr>
                    <tr>
                        <td class="g">7</td>
                        <td class="h">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );

    // Release pointer: row should move after merged row
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
                        <td class="d">3</td>
                        <td rowspan="3" class="c">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                    </tr>
                    <tr class="">
                        <td class="f">6</td>
                    </tr>
                    <tr class="">
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td class="g">7</td>
                        <td class="h">8</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should not allow dragging a merged row", async () => {
    const { el } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td class="a">[]1</td>
                        <td class="b">2</td>
                    </tr>
                    <tr>
                        <td rowspan="2" class="c">3</td>
                        <td class="d">4</td>
                    </tr>
                    <tr>
                        <td class="e">5</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );

    await expectElementCount(".o-we-table-menu", 0);
    // Hover over a cell in the merged row
    await hover(el.querySelector("td.c"));
    await waitFor("[data-type='row'].o-we-table-menu");
    const rowMenu = document.querySelector("[data-type='row'].o-we-table-menu");
    const rowMenuRect = rowMenu.getBoundingClientRect();
    // Start a long press on the merged row menu
    await manuallyDispatchProgrammaticEvent(rowMenu, "pointerdown", {
        clientX: rowMenuRect.x,
        clientY: rowMenuRect.y + rowMenuRect.height / 2,
    });
    // Table drag-drop overlay activates after a 200ms long press.
    // Wait 300ms to ensure reliability in tests.
    await delay(300);
    // Drag overlay should not appear for merged rows
    await expectElementCount(".o-we-table-drag-drop", 0);
});

test("undo/redo should work correctly after dragging and dropping a row", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table m-4">
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
            <table class="table table-bordered o_table m-4">
                <tbody>
                    <tr><td class="b">2</td></tr>
                    <tr class=""><td class="c">3</td></tr>
                    <tr><td class="a">[]1</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -13px 0px 12px;"><br></p>
        `)
    );
    // Undo the drag and drop
    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table m-4">
                <tbody>
                    <tr><td class="a">[]1</td></tr>
                    <tr><td class="b">2</td></tr>
                    <tr><td class="c">3</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -13px 0px 12px;"><br></p>
        `)
    );
    // Redo the drag and drop
    redo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <table class="table table-bordered o_table m-4">
                <tbody>
                    <tr><td class="b">2</td></tr>
                    <tr><td class="c">3</td></tr>
                    <tr><td class="a">[]1</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -13px 0px 12px;"><br></p>
        `)
    );
});
