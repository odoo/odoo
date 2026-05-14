import { describe, expect, manuallyDispatchProgrammaticEvent, test } from "@odoo/hoot";
import { unformat } from "./_helpers/format";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";

// Note: we allow ±2px tolerance because DOM sizes can differ slightly
// across environments (subpixel layout + browser rounding).
const TOLERANCE = 2;

describe("table resize", () => {
    describe("row", () => {
        test.tags("desktop");
        test("expand first row by dragging its bottom edge downward", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr><td><p><br></p></td></tr>
                            <tr><td><p><br></p></td></tr>
                            <tr><td><p><br></p></td></tr>
                        </tbody>
                    </table>
                `)
            );

            const targetRow = el.querySelector("table tbody tr");
            const targetRect = targetRow.getBoundingClientRect();

            const startX = targetRect.left + targetRect.width / 2;
            const startY = targetRect.bottom;

            const heightBefore = targetRect.height;
            const dragDelta = heightBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetRow, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetRow, "pointermove", {
                clientX: startX,
                clientY: startY + dragDelta,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetRow, "pointerup", {
                clientX: startX,
                clientY: startY + dragDelta,
            });
            await animationFrame();

            // Bottom-edge row resize should increase height
            const expectedHeight = Math.round(heightBefore + dragDelta);
            const actualHeight = parseFloat(targetRow.style.height);

            expect(Math.abs(actualHeight - expectedHeight) <= TOLERANCE).toBe(true);
        });

        test.tags("desktop");
        test("shrink first row by dragging its top edge downward", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 100px">
                                <td><p><br></p></td>
                            </tr>
                            <tr style="height: 100px">
                                <td><p><br></p></td>
                            </tr>
                            <tr style="height: 100px">
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const row1 = table.rows[0];
            const row2 = table.rows[1];
            const row3 = table.rows[2];

            const targetRect = row1.getBoundingClientRect();
            const startX = targetRect.left + targetRect.width / 2;
            const startY = targetRect.top;

            const heightBefore = parseFloat(row1.style.height);
            const dragDelta = heightBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(row1, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(row1, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "pointermove", {
                clientX: startX,
                clientY: startY + dragDelta,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "pointerup", {
                clientX: startX,
                clientY: startY + dragDelta,
            });
            await animationFrame();

            // Top-edge first row: shrinks row + shifts table down (margin-top)
            const row1HeightAfter = parseFloat(row1.style.height);
            expect(row1HeightAfter).toBeLessThan(heightBefore);
            expect(Math.abs(row1HeightAfter - (heightBefore - dragDelta)) <= TOLERANCE).toBe(true);

            const marginTopAfter = parseFloat(table.style.marginTop);
            expect(Math.abs(marginTopAfter - dragDelta) <= TOLERANCE).toBe(true);

            // Other rows unchanged
            expect(parseFloat(row2.style.height)).toBe(heightBefore);
            expect(parseFloat(row3.style.height)).toBe(heightBefore);
        });

        test.tags("desktop");
        test("shrink last row by dragging bottom edge upward", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 100px">
                                <td><p><br></p></td>
                            </tr>
                            <tr style="height: 100px">
                                <td><p><br></p></td>
                            </tr>
                            <tr style="height: 100px">
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const row1 = table.rows[0];
            const row2 = table.rows[1];
            const row3 = table.rows[2];

            const targetRect = row3.getBoundingClientRect();
            const startX = targetRect.left + targetRect.width / 2;
            const startY = targetRect.bottom;

            const heightBefore = parseFloat(row3.style.height);
            const dragDelta = heightBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(row3, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(row3, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(row3, "pointermove", {
                clientX: startX,
                clientY: startY - dragDelta,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(row3, "pointerup", {
                clientX: startX,
                clientY: startY - dragDelta,
            });
            await animationFrame();

            // Bottom-edge last row: only row shrinks (no margin change)
            const row3HeightAfter = parseFloat(row3.style.height);
            expect(row3HeightAfter).toBeLessThan(heightBefore);
            expect(Math.abs(row3HeightAfter - (heightBefore - dragDelta)) <= TOLERANCE).toBe(true);

            // Other rows unchanged
            expect(parseFloat(row1.style.height)).toBe(heightBefore);
            expect(parseFloat(row2.style.height)).toBe(heightBefore);
        });
    });

    describe("column", () => {
        test.tags("desktop");
        test("expand table first column by dragging right edge outward & table width remains unchanged", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <colgroup>
                            <col style="width: 600px;">
                            <col style="width: 600px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const secondRow = table.rows[1];
            const targetCell = secondRow.cells[0];

            const columns = table.querySelectorAll("col");
            const column1 = columns[0];
            const column2 = columns[1];

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            const columnWidthBefore = parseFloat(column1.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // Table width remains unchanged
            expect(table.offsetWidth).toBe(tableWidthBefore);

            // Column widths updated correctly
            const column1After = parseFloat(column1.style.width);
            const column2After = parseFloat(column2.style.width);

            expect(Math.abs(column1After - (columnWidthBefore + dragDelta)) <= TOLERANCE).toBe(
                true
            );
            expect(Math.abs(column2After - (columnWidthBefore - dragDelta)) <= TOLERANCE).toBe(
                true
            );

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });

        test.tags("desktop");

        test("expand table first column by dragging right edge outward without initial colgroup", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <tbody>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const secondRow = table.rows[1];
            const targetCell = secondRow.cells[0];

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            // There is no colgroup initially.
            let columns = table.querySelectorAll("col");
            expect(columns.length).toBe(0);

            const columnWidthBefore = parseFloat(getComputedStyle(targetCell).width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            columns = table.querySelectorAll("col");
            expect(columns.length).toBe(2);

            const column1 = columns[0];
            const column2 = columns[1];

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // Dispatch pointerup on the cell to ensure selection staging is
            // skipped without triggering the staged mutations warning.
            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // Table width remains unchanged
            expect(table.offsetWidth).toBe(tableWidthBefore);

            // Column widths updated correctly
            const column1After = parseFloat(column1.style.width);
            const column2After = parseFloat(column2.style.width);

            expect(Math.abs(column1After - (columnWidthBefore + dragDelta)) <= TOLERANCE).toBe(
                true
            );
            expect(Math.abs(column2After - (columnWidthBefore - dragDelta)) <= TOLERANCE).toBe(
                true
            );

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });

        test.tags("desktop");
        test("shrink table first column by dragging left edge inward & table width decreases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <colgroup>
                            <col style="width: 600px;">
                            <col style="width: 600px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const secondRow = table.rows[1];
            const targetCell = secondRow.cells[0];

            const columns = table.querySelectorAll("col");
            const column1 = columns[0];
            const column2 = columns[1];

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.left;
            const startY = targetRect.top + targetRect.height / 2;

            const columnWidthBefore = parseFloat(column1.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // Table width decreases
            expect(table.offsetWidth).toBeLessThan(tableWidthBefore);

            // First column shrinks
            const column1After = parseFloat(column1.style.width);
            expect(column1After).toBeLessThan(columnWidthBefore);
            expect(Math.abs(column1After - (columnWidthBefore - dragDelta)) <= TOLERANCE).toBe(
                true
            );

            // Neighbor column remains unchanged
            expect(parseFloat(column2.style.width)).toBe(columnWidthBefore);

            // Table shifts using margin-left
            const marginLeftAfter = parseFloat(table.style.marginLeft);
            expect(Math.abs(marginLeftAfter - dragDelta) <= TOLERANCE).toBe(true);

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });

        test.tags("desktop");
        test("expand table last column by dragging right edge outward & table width increases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <colgroup>
                            <col style="width: 600px;">
                            <col style="width: 600px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const secondRow = table.rows[1];
            const targetCell = secondRow.cells[1];

            const columns = table.querySelectorAll("col");
            const column1 = columns[0];
            const column2 = columns[1];

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            const columnWidthBefore = parseFloat(column2.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // Table width increases
            expect(table.offsetWidth).toBeGreaterThan(tableWidthBefore);

            // Last column expands
            const column2After = parseFloat(column2.style.width);
            expect(column2After).toBeGreaterThan(columnWidthBefore);
            expect(Math.abs(column2After - (columnWidthBefore + dragDelta)) <= TOLERANCE).toBe(
                true
            );

            // First column remains unchanged
            expect(parseFloat(column1.style.width)).toBe(columnWidthBefore);

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });

        test.tags("desktop");
        test("shrink table last column with colspan by dragging right edge inward & table width decreases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <colgroup>
                            <col style="width: 600px;">
                            <col style="width: 600px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td colspan="2"><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");
            const targetRow = table.rows[1];
            const targetCell = targetRow.cells[1];

            const columns = table.querySelectorAll("col");
            const column1 = columns[0];
            const column2 = columns[1];

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            // BEFORE: use colgroup widths
            const columnWidthBefore = parseFloat(column2.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX - dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX - dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // AFTER: use updated colgroup widths
            const columnWidthAfter = parseFloat(column2.style.width);
            const tableWidthAfter = parseFloat(table.style.width);

            const expectedColumnWidth = columnWidthBefore - dragDelta;
            const expectedTableWidth = tableWidthBefore - dragDelta;

            // Last column shrinks
            expect(Math.abs(columnWidthAfter - expectedColumnWidth) <= TOLERANCE).toBe(true);

            // Table shrinks
            expect(Math.abs(tableWidthAfter - expectedTableWidth) <= TOLERANCE).toBe(true);

            // First column unchanged
            expect(parseFloat(column1.style.width)).toBe(parseFloat(columnWidthBefore));

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });

        test.tags("desktop");
        test("expand table last column with rowspan by dragging right edge outward & table width increases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <colgroup>
                            <col style="width: 600px;">
                            <col style="width: 600px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td><p><br></p></td>
                                <td rowspan="2"><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");
            const targetRow = table.rows[0];
            const targetCell = targetRow.cells[1]; // last column (rowspan cell)

            const columns = table.querySelectorAll("col");
            const column1 = columns[0];
            const column2 = columns[1];

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            // BEFORE: use colgroup widths
            const columnWidthBefore = parseFloat(column2.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // AFTER
            const columnWidthAfter = parseFloat(column2.style.width);
            const tableWidthAfter = parseFloat(table.style.width);

            const expectedColumnWidth = columnWidthBefore + dragDelta;
            const expectedTableWidth = tableWidthBefore + dragDelta;

            // Last column expands
            expect(Math.abs(columnWidthAfter - expectedColumnWidth) <= TOLERANCE).toBe(true);

            // Table expands
            expect(Math.abs(tableWidthAfter - expectedTableWidth) <= TOLERANCE).toBe(true);

            // First column unchanged
            expect(parseFloat(column1.style.width)).toBe(columnWidthBefore);

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });

        test.tags("desktop");
        test("shrink table last column by dragging right edge inward & table width decreases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");
            const targetRow = table.rows[0];
            const targetCell = targetRow.cells[1]; // last column

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            // BEFORE: use rendered layout (no colgroup yet)
            const columnWidthBefore = targetRect.width;
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = columnWidthBefore / 2;

            // Trigger resize via pointer hover
            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
                clientX: startX - dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
                clientX: startX - dragDelta,
                clientY: startY,
            });
            await animationFrame();

            // AFTER: colgroup should now exist
            const columns = table.querySelectorAll("col");
            const column2 = columns[1];

            const columnWidthAfter = parseFloat(column2.style.width);
            const tableWidthAfter = parseFloat(table.style.width);

            const expectedColumnWidth = columnWidthBefore - dragDelta;
            const expectedTableWidth = tableWidthBefore - dragDelta;

            expect(Math.abs(columnWidthAfter - expectedColumnWidth) <= TOLERANCE).toBe(true);
            expect(Math.abs(tableWidthAfter - expectedTableWidth) <= TOLERANCE).toBe(true);

            // Width should be applied to <col> elements, not <td> elements
            columns.forEach((col) => expect(col.style.width).not.toBe(""));
            table.querySelectorAll("td").forEach((td) => expect(td.style.width).toBe(""));
        });
    });
});

describe("column resize", () => {
    test.tags("desktop");
    test("expand first column by dragging its right edge outward & row width remains unchanged", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                    <div class="row" style="width: 1600px;">
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint">[]</p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                    </div>
                </div>
            `)
        );

        const row = el.querySelector(".o_text_columns .row");
        const col1 = row.firstChild;
        const col2 = col1.nextElementSibling;
        const col3 = col2.nextElementSibling;
        const col4 = col3.nextElementSibling;

        const rect = col1.getBoundingClientRect();
        const startX = rect.right;
        const startY = rect.top + rect.height / 2;

        const colWidthBefore = parseFloat(col1.style.width);
        const rowWidthBefore = row.offsetWidth;
        const dragDelta = colWidthBefore / 4;

        // Trigger resize via pointer hover
        manuallyDispatchProgrammaticEvent(col1, "pointermove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(col1).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(col1, "pointerdown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "pointermove", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "pointerup", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        const col1After = parseFloat(col1.style.width);
        const col2After = parseFloat(col2.style.width);
        const rowWidthAfter = row.offsetWidth;

        // Middle resize: neighbor compensates, row width stays fixed
        expect(col1After).toBeGreaterThan(colWidthBefore);
        expect(rowWidthAfter).toBe(rowWidthBefore);

        expect(Math.abs(col1After - (colWidthBefore + dragDelta)) <= TOLERANCE).toBe(true);
        expect(Math.abs(col2After - (colWidthBefore - dragDelta)) <= TOLERANCE).toBe(true);

        // Unaffected columns stay unchanged
        expect(parseFloat(col3.style.width)).toBe(colWidthBefore);
        expect(parseFloat(col4.style.width)).toBe(colWidthBefore);
    });

    test.tags("desktop");
    test("shrink first column by dragging its left edge inward & row width decreases", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                    <div class="row" style="width: 1600px;">
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint">[]</p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                    </div>
                </div>
            `)
        );

        const row = el.querySelector(".o_text_columns .row");
        const col1 = row.firstChild;
        const col2 = col1.nextElementSibling;
        const col3 = col2.nextElementSibling;
        const col4 = col3.nextElementSibling;

        const targetRect = col1.getBoundingClientRect();
        const startX = targetRect.left;
        const startY = targetRect.top + targetRect.height / 2;

        const colWidthBefore = parseFloat(col1.style.width);
        const rowWidthBefore = row.offsetWidth;
        const dragDelta = colWidthBefore / 4;

        // Trigger resize via pointer hover
        manuallyDispatchProgrammaticEvent(col1, "pointermove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(col1).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(col1, "pointerdown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "pointermove", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "pointerup", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        const colWidthAfter = parseFloat(col1.style.width);
        const rowWidthAfter = row.offsetWidth;

        // First resize: row width decreases and margin-left shifts
        expect(colWidthAfter).toBeLessThan(colWidthBefore);
        expect(rowWidthAfter).toBeLessThan(rowWidthBefore);

        const expectedColWidth = colWidthBefore - dragDelta;
        const expectedRowWidth = rowWidthBefore - dragDelta;
        const marginLeftAfter = parseFloat(row.style.marginLeft);

        expect(Math.abs(colWidthAfter - expectedColWidth) <= TOLERANCE).toBe(true);
        expect(Math.abs(parseFloat(row.style.width) - expectedRowWidth) <= TOLERANCE).toBe(true);
        expect(Math.abs(marginLeftAfter - dragDelta) <= TOLERANCE).toBe(true);

        // Unaffected columns stay unchanged
        expect(parseFloat(col2.style.width)).toBe(colWidthBefore);
        expect(parseFloat(col3.style.width)).toBe(colWidthBefore);
        expect(parseFloat(col4.style.width)).toBe(colWidthBefore);
    });

    test.tags("desktop");
    test("expand last column by dragging its right edge outward & row width increases", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                    <div class="row" style="width: 1600px;">
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint">[]</p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 400px;">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                    </div>
                </div>
            `)
        );

        const row = el.querySelector(".o_text_columns .row");
        const col1 = row.firstChild;
        const col2 = col1.nextElementSibling;
        const col3 = col2.nextElementSibling;
        const col4 = col3.nextElementSibling;

        const targetRect = col4.getBoundingClientRect();
        const startX = targetRect.right;
        const startY = targetRect.top + targetRect.height / 2;

        const colWidthBefore = parseFloat(col4.style.width);
        const rowWidthBefore = row.offsetWidth;
        const dragDelta = colWidthBefore / 4;

        // Trigger resize via pointer hover
        manuallyDispatchProgrammaticEvent(col4, "pointermove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(col4).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(col4, "pointerdown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "pointermove", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "pointerup", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        const colWidthAfter = parseFloat(col4.style.width);
        const rowWidthAfter = row.offsetWidth;

        // Last resize: row width increases
        expect(colWidthAfter).toBeGreaterThan(colWidthBefore);
        expect(rowWidthAfter).toBeGreaterThan(rowWidthBefore);

        expect(Math.abs(colWidthAfter - (colWidthBefore + dragDelta)) <= TOLERANCE).toBe(true);
        expect(
            Math.abs(parseFloat(row.style.width) - (rowWidthBefore + dragDelta)) <= TOLERANCE
        ).toBe(true);

        // Unaffected columns stay unchanged
        expect(parseFloat(col1.style.width)).toBe(colWidthBefore);
        expect(parseFloat(col2.style.width)).toBe(colWidthBefore);
        expect(parseFloat(col3.style.width)).toBe(colWidthBefore);
    });

    test.tags("desktop");
    test("sets widths when shrinking last column by dragging its right edge inward (no initial widths)", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                    <div class="row">
                        <div class="col-4 o-contenteditable-true" contenteditable="true">
                            <p o-we-hint-text="Empty column" class="o-we-hint">[]</p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true">
                            <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                        </div>
                    </div>
                </div>
            `)
        );

        const row = el.querySelector(".o_text_columns .row");
        const targetColumn = row.lastChild;

        const targetRect = targetColumn.getBoundingClientRect();
        const startX = targetRect.right;
        const startY = targetRect.top + targetRect.height / 2;

        const columnWidthBefore = targetRect.width;
        const rowWidthBefore = row.offsetWidth;
        const dragDelta = columnWidthBefore / 4;

        // Trigger resize via pointer hover
        manuallyDispatchProgrammaticEvent(targetColumn, "pointermove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(targetColumn).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(targetColumn, "pointerdown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(targetColumn, "pointermove", {
            clientX: startX - dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(targetColumn, "pointerup", {
            clientX: startX - dragDelta,
            clientY: startY,
        });
        await animationFrame();

        // No initial widths: plugin sets inline widths during resize.
        const expectedColWidth = Math.round(columnWidthBefore - dragDelta);
        const expectedRowWidth = Math.round(rowWidthBefore - dragDelta);

        const actualColWidth = parseFloat(targetColumn.style.width);
        const actualRowWidth = parseFloat(row.style.width);

        expect(Math.abs(actualColWidth - expectedColWidth) <= TOLERANCE).toBe(true);
        expect(Math.abs(actualRowWidth - expectedRowWidth) <= TOLERANCE).toBe(true);
    });
});

test.tags("desktop");
test("inner table resize is clamped by parent table boundary", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table class="table table-bordered o_table" style="width: 800px;">
                <colgroup>
                    <col style="width: 800px;">
                </colgroup>
                <tbody>
                    <tr>
                        <td>
                            <table class="table table-bordered o_table" style="width: 500px; margin-left: 100px;">
                                <colgroup>
                                    <col style="width: 200px;">
                                    <col style="width: 300px;">
                                </colgroup>
                                <tbody>
                                    <tr>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                    </tr>
                </tbody>
            </table>
        `)
    );

    const outerTable = el.querySelectorAll("table")[0];
    const innerTable = el.querySelectorAll("table")[1];
    const targetCell = innerTable.rows[0].cells[1];
    const targetRect = targetCell.getBoundingClientRect();
    const startX = targetRect.right;
    const startY = targetRect.top + targetRect.height / 2;
    const tableWidthBefore = innerTable.offsetWidth;

    // Trigger resize via pointer hover
    manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: startX,
        clientY: startY,
    });
    await animationFrame();

    manuallyDispatchProgrammaticEvent(targetCell, "pointerdown", {
        clientX: startX,
        clientY: startY,
    });
    await animationFrame();

    // First resize: width should increase normally
    manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: startX + 100,
        clientY: startY,
    });
    await animationFrame();

    const tableWidthAfterSmallResize = innerTable.offsetWidth;
    expect(tableWidthAfterSmallResize).toBeGreaterThan(tableWidthBefore);

    // Try to resize far beyond parent boundary
    manuallyDispatchProgrammaticEvent(targetCell, "pointermove", {
        clientX: startX + 1000,
        clientY: startY,
    });
    await animationFrame();

    manuallyDispatchProgrammaticEvent(targetCell, "pointerup", {
        clientX: startX + 1000,
        clientY: startY,
    });
    await animationFrame();

    const tableWidthAfterClampedResize = innerTable.offsetWidth;
    // Width should stop increasing once boundary is reached
    expect(tableWidthAfterClampedResize).toBe(tableWidthAfterSmallResize);
    // Inner table should remain inside parent boundary
    expect(innerTable.offsetWidth + parseFloat(innerTable.style.marginLeft)).toBeLessThan(
        outerTable.clientWidth
    );
});

test.tags("desktop");
test("text columns first column resize outward is clamped by parent table boundary", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table class="table table-bordered o_table" style="width: 900px;">
                <colgroup>
                    <col style="width: 900px;">
                </colgroup>
                <tbody>
                    <tr>
                        <td>
                            <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                                <div class="row" style="width: 500px; margin-left: 100px !important;">
                                    <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 200px;">
                                        <p o-we-hint-text="Empty column" class="o-we-hint">[]</p>
                                    </div>
                                    <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 300px;">
                                        <p o-we-hint-text="Empty column" class="o-we-hint"><br></p>
                                    </div>
                                </div>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        `)
    );

    const table = el.querySelector("table");
    const row = el.querySelector(".o_text_columns .row");
    const targetColumn = row.firstElementChild;
    const targetRect = targetColumn.getBoundingClientRect();
    const startX = targetRect.left;
    const startY = targetRect.top + targetRect.height / 2;
    const rowWidthBefore = row.offsetWidth;
    const marginLeftBefore = parseFloat(row.style.marginLeft);

    // Trigger resize via pointer hover.
    manuallyDispatchProgrammaticEvent(targetColumn, "pointermove", {
        clientX: startX,
        clientY: startY,
    });
    await animationFrame();

    manuallyDispatchProgrammaticEvent(targetColumn, "pointerdown", {
        clientX: startX,
        clientY: startY,
    });
    await animationFrame();

    // First resize: width should increase normally.
    manuallyDispatchProgrammaticEvent(targetColumn, "pointermove", {
        clientX: startX - 50,
        clientY: startY,
    });
    await animationFrame();

    const rowWidthAfterSmallResize = row.offsetWidth;
    expect(rowWidthAfterSmallResize).toBeGreaterThan(rowWidthBefore);

    // Try to resize far beyond parent table boundary.
    manuallyDispatchProgrammaticEvent(targetColumn, "pointermove", {
        clientX: startX - 1200,
        clientY: startY,
    });
    await animationFrame();

    manuallyDispatchProgrammaticEvent(targetColumn, "pointerup", {
        clientX: startX - 1200,
        clientY: startY,
    });
    await animationFrame();

    const rowWidthAfterClampedResize = row.offsetWidth;
    const marginLeftAfter = parseFloat(row.style.marginLeft);
    // Width should stop increasing once boundary is reached.
    expect(rowWidthAfterClampedResize).toBe(rowWidthAfterSmallResize);
    // Row should remain inside table boundary.
    expect(row.offsetWidth + marginLeftAfter).toBeLessThan(table.clientWidth);
    // Margin-left should not move beyond available space.
    expect(marginLeftAfter).toBeLessThan(marginLeftBefore);
});
