import { describe, expect, manuallyDispatchProgrammaticEvent, test } from "@odoo/hoot";
import { unformat } from "./_helpers/format";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";

// Note: we allow ±1px tolerance because DOM sizes can differ slightly
// across environments (subpixel layout + browser rounding).

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

            expect(Math.abs(actualHeight - expectedHeight) <= 1).toBe(true);
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
            expect(Math.abs(row1HeightAfter - (heightBefore - dragDelta)) <= 1).toBe(true);

            const marginTopAfter = parseFloat(table.style.marginTop);
            expect(Math.abs(marginTopAfter - dragDelta) <= 1).toBe(true);

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
            expect(Math.abs(row3HeightAfter - (heightBefore - dragDelta)) <= 1).toBe(true);

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
                        <tbody>
                            <tr>
                                <td style="width: 600px;"><p><br></p></td>
                                <td style="width: 600px;"><p><br></p></td>
                            </tr>
                            <tr>
                                <td style="width: 600px;"><p><br></p></td>
                                <td style="width: 600px;"><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const firstRow = table.rows[0];
            const secondRow = table.rows[1];

            const firstRowCell1 = firstRow.cells[0];
            const firstRowCell2 = firstRow.cells[1];

            const secondRowCell1 = secondRow.cells[0];
            const secondRowCell2 = secondRow.cells[1];

            const targetCell = secondRowCell1;

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            const cellWidthBefore = parseFloat(firstRowCell1.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = cellWidthBefore / 2;

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

            // Middle resize: table width stays fixed
            expect(table.offsetWidth).toBe(tableWidthBefore);

            // Only first row is resized (layout is driven by first row)
            const cell1After = parseFloat(firstRowCell1.style.width);
            const cell2After = parseFloat(firstRowCell2.style.width);

            // Neighbor shrinks to keep table width unchanged
            expect(Math.abs(cell1After - (cellWidthBefore + dragDelta)) <= 1).toBe(true);
            expect(Math.abs(cell2After - (cellWidthBefore - dragDelta)) <= 1).toBe(true);

            // Other rows remain unchanged
            expect(parseFloat(secondRowCell1.style.width)).toBe(cellWidthBefore);
            expect(parseFloat(secondRowCell2.style.width)).toBe(cellWidthBefore);
        });

        test.tags("desktop");
        test("shrink table first column by dragging left edge inward & table width decreases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <tbody>
                            <tr>
                                <td style="width: 600px;"><p><br></p></td>
                                <td style="width: 600px;"><p><br></p></td>
                            </tr>
                            <tr>
                                <td style="width: 600px;"><p><br></p></td>
                                <td style="width: 600px;"><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const firstRow = table.rows[0];
            const secondRow = table.rows[1];

            const firstRowCell1 = firstRow.cells[0];
            const firstRowCell2 = firstRow.cells[1];

            const secondRowCell1 = secondRow.cells[0];
            const secondRowCell2 = secondRow.cells[1];

            const targetCell = secondRowCell1;

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.left;
            const startY = targetRect.top + targetRect.height / 2;

            const cellWidthBefore = parseFloat(firstRowCell1.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = cellWidthBefore / 2;

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

            // First resize: table width decreases
            expect(table.offsetWidth).toBeLessThan(tableWidthBefore);

            // Only first row is resized (layout is driven by first row)
            const cell1After = parseFloat(firstRowCell1.style.width);
            expect(cell1After).toBeLessThan(cellWidthBefore);
            expect(Math.abs(cell1After - (cellWidthBefore - dragDelta)) <= 1).toBe(true);

            // Neighbor doesn't change for "first" case
            expect(parseFloat(firstRowCell2.style.width)).toBe(cellWidthBefore);

            // First resize: table shifts using margin-left
            const marginLeftAfter = parseFloat(table.style.marginLeft);
            expect(Math.abs(marginLeftAfter - dragDelta) <= 1).toBe(true);

            // Other rows remain unchanged
            expect(parseFloat(secondRowCell1.style.width)).toBe(cellWidthBefore);
            expect(parseFloat(secondRowCell2.style.width)).toBe(cellWidthBefore);
        });

        test.tags("desktop");
        test("expand table last column by dragging right edge outward & table width increases", async () => {
            const { el } = await setupEditor(
                unformat(`
                    <table class="table table-bordered o_table" style="width: 1200px;">
                        <tbody>
                            <tr>
                                <td style="width: 600px;"><p><br></p></td>
                                <td style="width: 600px;"><p><br></p></td>
                            </tr>
                            <tr>
                                <td style="width: 600px;"><p><br></p></td>
                                <td style="width: 600px;"><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                `)
            );

            const table = el.querySelector("table");

            const firstRow = table.rows[0];
            const secondRow = table.rows[1];

            const firstRowCell1 = firstRow.cells[0];
            const firstRowCell2 = firstRow.cells[1];

            const secondRowCell1 = secondRow.cells[0];
            const secondRowCell2 = secondRow.cells[1];

            const targetCell = secondRowCell2;

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            const cellWidthBefore = parseFloat(firstRowCell1.style.width);
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = cellWidthBefore / 2;

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

            // Last resize: table width increases
            expect(table.offsetWidth).toBeGreaterThan(tableWidthBefore);

            // Only first row is resized (layout is driven by first row)
            const lastCellAfter = parseFloat(firstRowCell2.style.width);
            expect(lastCellAfter).toBeGreaterThan(cellWidthBefore);
            expect(Math.abs(lastCellAfter - (cellWidthBefore + dragDelta)) <= 1).toBe(true);

            // Other first-row cell stays unchanged
            expect(parseFloat(firstRowCell1.style.width)).toBe(cellWidthBefore);

            // Other rows remain unchanged
            expect(parseFloat(secondRowCell1.style.width)).toBe(cellWidthBefore);
            expect(parseFloat(secondRowCell2.style.width)).toBe(cellWidthBefore);
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
            const targetRow = table.querySelectorAll("tr")[0];
            const targetCell = targetRow.lastChild;

            const targetRect = targetCell.getBoundingClientRect();
            const startX = targetRect.right;
            const startY = targetRect.top + targetRect.height / 2;

            const cellWidthBefore = targetRect.width;
            const tableWidthBefore = table.offsetWidth;
            const dragDelta = cellWidthBefore / 2;

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

            // Last resize: both last cell and table width shrink
            const expectedCellWidth = Math.round(cellWidthBefore - dragDelta);
            const expectedTableWidth = Math.round(tableWidthBefore - dragDelta);

            const actualCellWidth = parseFloat(targetCell.style.width);
            const actualTableWidth = parseFloat(table.style.width);

            expect(Math.abs(actualCellWidth - expectedCellWidth) <= 1).toBe(true);
            expect(Math.abs(actualTableWidth - expectedTableWidth) <= 1).toBe(true);
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

        expect(Math.abs(col1After - (colWidthBefore + dragDelta)) <= 1).toBe(true);
        expect(Math.abs(col2After - (colWidthBefore - dragDelta)) <= 1).toBe(true);

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

        expect(Math.abs(colWidthAfter - expectedColWidth) <= 1).toBe(true);
        expect(Math.abs(parseFloat(row.style.width) - expectedRowWidth) <= 1).toBe(true);
        expect(Math.abs(marginLeftAfter - dragDelta) <= 1).toBe(true);

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

        expect(Math.abs(colWidthAfter - (colWidthBefore + dragDelta)) <= 1).toBe(true);
        expect(Math.abs(parseFloat(row.style.width) - (rowWidthBefore + dragDelta)) <= 1).toBe(
            true
        );

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

        expect(Math.abs(actualColWidth - expectedColWidth) <= 1).toBe(true);
        expect(Math.abs(actualRowWidth - expectedRowWidth) <= 1).toBe(true);
    });
});
