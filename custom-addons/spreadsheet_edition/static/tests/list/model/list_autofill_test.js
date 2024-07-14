/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";

import * as spreadsheet from "@odoo/o-spreadsheet";
const { toCartesian } = spreadsheet.helpers;
import { getCell, getCellFormula, getCellValue } from "@spreadsheet/../tests/utils/getters";
import {
    autofill,
    selectCell,
    setCellContent,
    setCellFormat,
    setCellStyle,
} from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/utils/list";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

/**
 * Get the computed value that would be autofilled starting from the given xc.
 * The starting xc should contains a List formula
 */
function getListAutofillValue(model, xc, { direction, steps }) {
    const content = getCellFormula(model, xc);
    const column = ["left", "right"].includes(direction);
    const increment = ["left", "top"].includes(direction) ? -steps : steps;
    return model.getters.getNextListValue(content, column, increment);
}

QUnit.module("spreadsheet > list autofill", {}, () => {
    QUnit.test("Autofill list values", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        // From value to value
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "C4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "right", steps: 1 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "left", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "C5")
        );
        assert.strictEqual(
            getListAutofillValue(model, "C3", { direction: "bottom", steps: 3 }),
            `=ODOO.LIST(1,5,"date")`
        );
        assert.strictEqual(getListAutofillValue(model, "C3", { direction: "right", steps: 4 }), "");
        // From value to header
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "left", steps: 1 }),
            getCellFormula(model, "A4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 2 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B4", { direction: "top", steps: 3 }),
            getCellFormula(model, "B1")
        );
        // From header to header
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "right", steps: 1 }),
            getCellFormula(model, "C3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "right", steps: 2 }),
            getCellFormula(model, "D3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "left", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B3", { direction: "top", steps: 1 }),
            getCellFormula(model, "B2")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "A5")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "top", steps: 1 }),
            getCellFormula(model, "A3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A4", { direction: "bottom", steps: 2 }),
            `=ODOO.LIST(1,5,"foo")`
        );
        assert.strictEqual(getListAutofillValue(model, "A4", { direction: "top", steps: 4 }), "");
        // From header to value
        assert.strictEqual(
            getListAutofillValue(model, "B2", { direction: "bottom", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "B2", { direction: "bottom", steps: 2 }),
            getCellFormula(model, "B4")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A3", { direction: "right", steps: 1 }),
            getCellFormula(model, "B3")
        );
        assert.strictEqual(
            getListAutofillValue(model, "A3", { direction: "right", steps: 5 }),
            getCellFormula(model, "F3")
        );
        assert.strictEqual(getListAutofillValue(model, "A3", { direction: "right", steps: 6 }), "");
    });

    QUnit.test("Autofill list correctly update the cache", async function (assert) {
        const { model } = await createSpreadsheetWithList({ linesNumber: 1 });
        autofill(model, "A2", "A3");
        assert.strictEqual(getCellValue(model, "A3"), "Loading...");
        await nextTick(); // Await for the batch collection of missing ids
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "A3"), 1);
    });

    QUnit.test(
        "Autofill with references works like any regular function (no custom autofill)",
        async function (assert) {
            const { model } = await createSpreadsheetWithList();
            setCellContent(model, "A1", '=ODOO.LIST(1, A1,"probability")');
            selectCell(model, "A1");

            model.dispatch("AUTOFILL_SELECT", { col: 0, row: 1 });
            model.dispatch("AUTOFILL");
            assert.equal(getCellFormula(model, "A2"), '=ODOO.LIST(1, A2,"probability")');
        }
    );

    QUnit.test("Tooltip of list formulas", async function (assert) {
        const { model } = await createSpreadsheetWithList();

        function getTooltip(xc, isColumn) {
            return model.getters.getTooltipListFormula(getCellFormula(model, xc), isColumn);
        }

        assert.strictEqual(getTooltip("A3", false), "Record #2");
        assert.strictEqual(getTooltip("A3", true), "Foo");
        assert.strictEqual(getTooltip("A1", false), "Foo");
        assert.strictEqual(getTooltip("A1", true), "Foo");
    });

    QUnit.test("Autofill list formula with missing listId", async function (assert) {
        const model = new spreadsheet.Model({
            sheets: [
                {
                    colNumber: 1,
                    rowNumber: 2,
                    cells: {
                        A1: { content: '=ODOO.LIST("1","1","date")' },
                        B1: { content: '=ODOO.LIST.HEADER("1","date")' },
                    },
                },
            ],
        });
        assert.strictEqual(
            getListAutofillValue(model, "A1", { direction: "bottom", steps: 1 }),
            '=ODOO.LIST("1","1","date")'
        );
        assert.strictEqual(
            getListAutofillValue(model, "B1", { direction: "bottom", steps: 1 }),
            '=ODOO.LIST.HEADER("1","date")'
        );
        assert.strictEqual(
            model.getters.getTooltipListFormula(getCellFormula(model, "A1"), false),
            "Missing list #1"
        );
        assert.strictEqual(
            model.getters.getTooltipListFormula(getCellFormula(model, "B1"), false),
            "Missing list #1"
        );
    });

    QUnit.test("Autofill list keeps format but neither style nor border", async function (assert) {
        const { model } = await createSpreadsheetWithList();
        // Change the format, style and borders of C2
        const sheetId = model.getters.getActiveSheetId();
        const { col, row } = toCartesian("C2");
        const border = {
            left: { style: "thin", color: "#000" },
        };
        const style = { textColor: "orange" };
        setCellFormat(model, "C2", "m/d/yyyy");
        setCellStyle(model, "C2", style);
        model.dispatch("SET_BORDER", { sheetId, col, row, border });

        // Change the format of C3
        setCellFormat(model, "C3", "d/m/yyyy");

        // Check that the format, style and border of C2 have been correctly applied
        autofill(model, "C2", "C3");
        const startingCell = getCell(model, "C2");
        assert.deepEqual(startingCell.style, style);
        assert.deepEqual(model.getters.getCellBorder({sheetId, col, row}).left, border.left);
        assert.equal(startingCell.format, "m/d/yyyy");

        // Check that the format of C2 has been correctly applied to C3 but not the style nor the border
        const filledCell = getCell(model, "C3");
        assert.equal(filledCell.style, undefined);
        assert.equal(model.getters.getCellBorder({sheetId, col, row: row + 1}), null);
        assert.equal(filledCell.format, "m/d/yyyy");
    });
});
