import { describe, expect, manuallyDispatchProgrammaticEvent, test } from "@odoo/hoot";
import { unformat } from "./_helpers/format";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";

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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(targetRow, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetRow, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetRow, "mousemove", {
                clientX: startX,
                clientY: startY + dragDelta,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetRow, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(row1, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(row1, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mousemove", {
                clientX: startX,
                clientY: startY + dragDelta,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(row3, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(row3, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mousemove", {
                clientX: startX,
                clientY: startY - dragDelta,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mouseup", {
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
            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mousemove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mousemove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mousemove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX - dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX + dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mouseup", {
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

            // Trigger resize via mouse hover
            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousedown", {
                clientX: startX,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mousemove", {
                clientX: startX - dragDelta,
                clientY: startY,
            });
            await animationFrame();

            manuallyDispatchProgrammaticEvent(targetCell, "mouseup", {
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

        // Trigger resize via mouse hover
        manuallyDispatchProgrammaticEvent(col1, "mousemove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(col1).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(col1, "mousedown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "mousemove", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

        // Trigger resize via mouse hover
        manuallyDispatchProgrammaticEvent(col1, "mousemove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(col1).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(col1, "mousedown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "mousemove", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

        // Trigger resize via mouse hover
        manuallyDispatchProgrammaticEvent(col4, "mousemove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(col4).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(col4, "mousedown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "mousemove", {
            clientX: startX + dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(document, "mouseup", {
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

        // Trigger resize via mouse hover
        manuallyDispatchProgrammaticEvent(targetColumn, "mousemove", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        expect(targetColumn).toHaveClass("o_resize_handle");

        manuallyDispatchProgrammaticEvent(targetColumn, "mousedown", {
            clientX: startX,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(targetColumn, "mousemove", {
            clientX: startX - dragDelta,
            clientY: startY,
        });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(targetColumn, "mouseup", {
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

describe("table reset", () => {
    describe("row", () => {
        test.tags("desktop");
        test("reset row size removes custom height", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 38px;">
                                <td>1</td>
                            </tr>
                            <tr style="height: 100px;">
                                <td class="a">2[]</td>
                            </tr>
                            <tr style="height: 38px;">
                                <td>3</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const row = table.rows[1];
            editor.shared.resize.resetHeight(row, {
                layoutContainer: table,
                elementsSelector: "tr",
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td>1</td>
                            </tr>
                            <tr>
                                <td class="a">2[]</td>
                            </tr>
                            <tr>
                                <td>3</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("reset row size preserves unrelated row heights", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 50px;">
                                <td>1</td>
                            </tr>
                            <tr style="height: 100px;">
                                <td class="a">2[]</td>
                            </tr>
                            <tr style="height: 200px;">
                                <td>3</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const row = table.rows[1];
            editor.shared.resize.resetHeight(row, {
                layoutContainer: table,
                elementsSelector: "tr",
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr style="height: 50px;">
                                <td>1</td>
                            </tr>
                            <tr>
                                <td class="a">2[]</td>
                            </tr>
                            <tr style="height: 200px;">
                                <td>3</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("reset row size removes table margin top", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="margin-top: 40px;">
                        <tbody>
                            <tr style="height: 100px;">
                                <td class="a">1[]</td>
                            </tr>
                            <tr style="height: 38px;">
                                <td>2</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const row = table.rows[0];
            editor.shared.resize.resetHeight(row, {
                layoutContainer: table,
                elementsSelector: "tr",
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder="" style="margin: 20px 0px -21px;"><br></p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td class="a">1[]</td>
                            </tr>
                            <tr>
                                <td>2</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });
    });

    describe("column", () => {
        test.tags("desktop");
        test("should redistribute excess width from current column to smaller columns", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 500px">
                        <colgroup>
                            <col style="width: 100px;">
                            <col style="width: 120px;">
                            <col style="width: 60px;">
                            <col style="width: 120px;">
                            <col style="width: 100px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td class="a">1</td>
                                <td class="b">2</td>
                                <td class="c">3[]</td>
                                <td class="d">4</td>
                                <td class="e">5</td>
                            </tr>
                            <tr>
                                <td class="f">6</td>
                                <td class="g">7</td>
                                <td class="h">8</td>
                                <td class="i">9</td>
                                <td class="j">10</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const targetColumn = table.querySelectorAll("col")[2];
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer: table,
                hasProxyElements: true,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td class="a">1</td>
                                <td class="b">2</td>
                                <td class="c">3[]</td>
                                <td class="d">4</td>
                                <td class="e">5</td>
                            </tr>
                            <tr>
                                <td class="f">6</td>
                                <td class="g">7</td>
                                <td class="h">8</td>
                                <td class="i">9</td>
                                <td class="j">10</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("should redistribute excess width from the current colspan column when resetting column sizes", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1182px">
                        <colgroup>
                            <col style="width: 236.188px;">
                            <col style="width: 236.188px;">
                            <col style="width: 312.125px;">
                            <col style="width: 160.25px;">
                            <col style="width: 236.25px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td>1</td>
                                <td class="a" colspan="2">2[]</td>
                                <td>3</td>
                                <td>4</td>
                            </tr>
                            <tr>
                                <td>5</td>
                                <td>6</td>
                                <td colspan="2">7</td>
                                <td>8</td>
                            </tr>
                            <tr>
                                <td>9</td>
                                <td>10</td>
                                <td>11</td>
                                <td>12</td>
                                <td>13</td>
                            </tr>
                            <tr>
                                <td>14</td>
                                <td colspan="2">15</td>
                                <td>16</td>
                                <td>17</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const targetColumn = table.querySelectorAll("col")[2];
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer: table,
                hasProxyElements: true,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td>1</td>
                                <td class="a" colspan="2">2[]</td>
                                <td>3</td>
                                <td>4</td>
                            </tr>
                            <tr>
                                <td>5</td>
                                <td>6</td>
                                <td colspan="2">7</td>
                                <td>8</td>
                            </tr>
                            <tr>
                                <td>9</td>
                                <td>10</td>
                                <td>11</td>
                                <td>12</td>
                                <td>13</td>
                            </tr>
                            <tr>
                                <td>14</td>
                                <td colspan="2">15</td>
                                <td>16</td>
                                <td>17</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("should redistribute excess width from larger columns to current column", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 700px">
                        <colgroup>
                            <col style="width: 120px;">
                            <col style="width: 80px;">
                            <col style="width: 60px;">
                            <col style="width: 180px;">
                            <col style="width: 60px;">
                            <col style="width: 80px;">
                            <col style="width: 120px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td class="a">1</td>
                                <td class="b">2</td>
                                <td class="c">3</td>
                                <td class="d">4[]</td>
                                <td class="e">5</td>
                                <td class="f">6</td>
                                <td class="g">7</td>
                            </tr>
                            <tr>
                                <td class="h">8</td>
                                <td class="i">9</td>
                                <td class="j">10</td>
                                <td class="k">11</td>
                                <td class="l">12</td>
                                <td class="m">13</td>
                                <td class="n">14</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const targetColumn = table.querySelectorAll("col")[3];
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer: table,
                hasProxyElements: true,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_table" style="width: 700px">
                        <colgroup>
                            <col style="width: 120px;">
                            <col style="width: 80px;">
                            <col>
                            <col>
                            <col>
                            <col style="width: 80px;">
                            <col style="width: 120px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td class="a">1</td>
                                <td class="b">2</td>
                                <td class="c">3</td>
                                <td class="d">4[]</td>
                                <td class="e">5</td>
                                <td class="f">6</td>
                                <td class="g">7</td>
                            </tr>
                            <tr>
                                <td class="h">8</td>
                                <td class="i">9</td>
                                <td class="j">10</td>
                                <td class="k">11</td>
                                <td class="l">12</td>
                                <td class="m">13</td>
                                <td class="n">14</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("reset column size removes table margin left", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 500px; margin-left: 100px;">
                        <colgroup>
                            <col style="width: 100px;">
                            <col style="width: 200px;">
                            <col style="width: 200px;">
                        </colgroup>
                        <tbody>
                            <tr>
                                <td class="a">1[]</td>
                                <td>2</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>4</td>
                                <td>5</td>
                                <td>6</td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );
            const table = el.querySelector("table");
            const targetColumn = table.querySelector("col");
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer: table,
                hasProxyElements: true,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td class="a">1[]</td>
                                <td>2</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>4</td>
                                <td>5</td>
                                <td>6</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `)
            );
        });
    });
});

describe("text columns", () => {
    describe("column reset", () => {
        test.tags("desktop");
        test("should redistribute excess width from middle column", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <div class="container o_text_columns o-contenteditable-false" contenteditable="false" style="width: 700px;">
                        <div class="row">
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 120px;"><p>1</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 80px;"><p>2</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 60px;"><p>3</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 180px;"><p>4[]</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 60px;"><p>5</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 80px;"><p>6</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 120px;"><p>7</p></div>
                        </div>
                    </div>
                `)
            );
            const layoutContainer = el.querySelector(".o_text_columns");
            const targetColumn = el.querySelector(".row > div:nth-child(4)");
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <div class="container o_text_columns o-contenteditable-false" contenteditable="false" style="width: 700px;">
                        <div class="row">
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 120px;"><p>1</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 80px;"><p>2</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>3</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>4[]</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>5</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 80px;"><p>6</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 120px;"><p>7</p></div>
                        </div>
                    </div>
                    <p data-selection-placeholder=""><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("reset first column size removes container margin left", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <div class="container o_text_columns o-contenteditable-false" contenteditable="false" style="width: 500px; margin-left: 100px;">
                        <div class="row">
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 100px;"><p>1[]</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 200px;"><p>2</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 200px;"><p>3</p></div>
                        </div>
                    </div>
                `)
            );
            const layoutContainer = el.querySelector(".o_text_columns");
            const targetColumn = el.querySelector(".row > div:first-child");
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                        <div class="row">
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>1[]</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>2</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>3</p></div>
                        </div>
                    </div>
                    <p data-selection-placeholder=""><br></p>
                `)
            );
        });

        test.tags("desktop");
        test("should redistribute excess width from end column", async () => {
            const { el, editor } = await setupEditor(
                unformat(`
                    <div class="container o_text_columns o-contenteditable-false" contenteditable="false" style="width: 400px;">
                        <div class="row">
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 100px;"><p>1</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 75px;"><p>2</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 75px;"><p>3</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 150px;"><p>4</p></div>
                        </div>
                    </div>
                `)
            );
            const layoutContainer = el.querySelector(".o_text_columns");
            const targetColumn = el.querySelector(".row > div:last-child");
            editor.shared.resize.resetWidth(targetColumn, {
                layoutContainer,
            });
            expect(getContent(el)).toBe(
                unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                        <div class="row">
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>1</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>2</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>3</p></div>
                            <div class="col-4 o-contenteditable-true" contenteditable="true"><p>4</p></div>
                        </div>
                    </div>
                    <p data-selection-placeholder=""><br></p>
                `)
            );
        });
    });
});

describe("fit to content (dblclick)", () => {
    test.tags("desktop");
    test("dblclick on row bottom edge resets heights of that row and its neighbor", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr style="height: 100px;"><td><p><br></p></td></tr>
                        <tr style="height: 100px;"><td><p><br></p></td></tr>
                        <tr style="height: 100px;"><td><p><br></p></td></tr>
                    </tbody>
                </table>
            `)
        );

        const table = el.querySelector("table");
        const firstRow = table.rows[0];
        const rowRect = firstRow.getBoundingClientRect();
        const clientX = rowRect.left + rowRect.width / 2;
        const clientY = rowRect.bottom;

        // Hover between first and second row.
        manuallyDispatchProgrammaticEvent(firstRow, "mousemove", {
            clientX,
            clientY,
        });
        await animationFrame();
        // Reset row heights with double click.
        manuallyDispatchProgrammaticEvent(firstRow, "dblclick", {
            clientX,
            clientY,
        });
        await animationFrame();

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr><td><p><br></p></td></tr>
                        <tr><td><p><br></p></td></tr>
                        <tr style="height: 100px;"><td><p><br></p></td></tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
            `)
        );
    });

    test.tags("desktop");
    test("dblclick on table middle-column edge resets both column widths and removes colgroup", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table" style="width: 1200px;">
                    <colgroup>
                        <col style="width: 500px;">
                        <col style="width: 700px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
            `)
        );

        const table = el.querySelector("table");
        const firstCell = table.rows[0].cells[0];
        const cellRect = firstCell.getBoundingClientRect();
        const clientX = cellRect.right;
        const clientY = cellRect.top + cellRect.height / 2;

        // Hover between both columns.
        manuallyDispatchProgrammaticEvent(firstCell, "mousemove", {
            clientX,
            clientY,
        });
        await animationFrame();
        // Reset column widths with double click.
        manuallyDispatchProgrammaticEvent(firstCell, "dblclick", {
            clientX,
            clientY,
        });
        await animationFrame();

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder="" class="o-horizontal-caret"><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
            `)
        );
    });

    test.tags("desktop");
    test("dblclick on text-column right edge resets both column widths and clears row width", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                    <div class="row" style="width: 800px;">
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 500px;">
                            <p><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true" style="width: 300px;">
                            <p><br></p>
                        </div>
                    </div>
                </div>
            `)
        );

        const row = el.querySelector(".o_text_columns .row");
        const firstColumn = row.firstChild;
        const columnRect = firstColumn.getBoundingClientRect();
        const clientX = columnRect.right;
        const clientY = columnRect.top + columnRect.height / 2;

        // Hover between both text columns.
        manuallyDispatchProgrammaticEvent(firstColumn, "mousemove", {
            clientX,
            clientY,
        });
        await animationFrame();
        // Reset column widths with double click.
        manuallyDispatchProgrammaticEvent(firstColumn, "dblclick", {
            clientX,
            clientY,
        });
        await animationFrame();

        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <div class="container o_text_columns o-contenteditable-false" contenteditable="false">
                    <div class="row">
                        <div class="col-4 o-contenteditable-true o_resize_handle" contenteditable="true">
                            <p><br></p>
                        </div>
                        <div class="col-4 o-contenteditable-true" contenteditable="true">
                            <p><br></p>
                        </div>
                    </div>
                </div>
                <p data-selection-placeholder=""><br></p>
            `)
        );
    });
});
