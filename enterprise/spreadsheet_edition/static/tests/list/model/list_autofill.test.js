import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import {
    autofill,
    selectCell,
    setCellContent,
    setCellFormat,
    setCellStyle,
} from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getCell, getCellFormula, getCellValue } from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { patchTranslations } from "@web/../tests/web_test_helpers";
const { toCartesian } = spreadsheet.helpers;

describe.current.tags("headless");
defineSpreadsheetModels();

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

test("Autofill list values", async function () {
    const { model } = await createSpreadsheetWithList();
    // From value to value
    expect(getListAutofillValue(model, "C3", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "C4")
    );
    expect(getListAutofillValue(model, "B4", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getListAutofillValue(model, "C3", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "D3")
    );
    expect(getListAutofillValue(model, "C3", { direction: "left", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getListAutofillValue(model, "C3", { direction: "bottom", steps: 2 })).toBe(
        getCellFormula(model, "C5")
    );
    expect(getListAutofillValue(model, "C3", { direction: "bottom", steps: 3 })).toBe(
        `=ODOO.LIST(1,5,"date")`
    );
    expect(getListAutofillValue(model, "C3", { direction: "right", steps: 4 })).toBe("");
    // From value to header
    expect(getListAutofillValue(model, "B4", { direction: "left", steps: 1 })).toBe(
        getCellFormula(model, "A4")
    );
    expect(getListAutofillValue(model, "B4", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getListAutofillValue(model, "B4", { direction: "top", steps: 2 })).toBe(
        getCellFormula(model, "B2")
    );
    expect(getListAutofillValue(model, "B4", { direction: "top", steps: 3 })).toBe(
        getCellFormula(model, "B1")
    );
    // From header to header
    expect(getListAutofillValue(model, "B3", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "C3")
    );
    expect(getListAutofillValue(model, "B3", { direction: "right", steps: 2 })).toBe(
        getCellFormula(model, "D3")
    );
    expect(getListAutofillValue(model, "B3", { direction: "left", steps: 1 })).toBe(
        getCellFormula(model, "A3")
    );
    expect(getListAutofillValue(model, "B1", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "B2")
    );
    expect(getListAutofillValue(model, "B3", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "B2")
    );
    expect(getListAutofillValue(model, "A4", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "A5")
    );
    expect(getListAutofillValue(model, "A4", { direction: "top", steps: 1 })).toBe(
        getCellFormula(model, "A3")
    );
    expect(getListAutofillValue(model, "A4", { direction: "bottom", steps: 2 })).toBe(
        `=ODOO.LIST(1,5,"foo")`
    );
    expect(getListAutofillValue(model, "A4", { direction: "top", steps: 4 })).toBe("");
    // From header to value
    expect(getListAutofillValue(model, "B2", { direction: "bottom", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getListAutofillValue(model, "B2", { direction: "bottom", steps: 2 })).toBe(
        getCellFormula(model, "B4")
    );
    expect(getListAutofillValue(model, "A3", { direction: "right", steps: 1 })).toBe(
        getCellFormula(model, "B3")
    );
    expect(getListAutofillValue(model, "A3", { direction: "right", steps: 5 })).toBe(
        getCellFormula(model, "F3")
    );
    expect(getListAutofillValue(model, "A3", { direction: "right", steps: 6 })).toBe("");
});

test("Autofill list correctly update the cache", async function () {
    const { model } = await createSpreadsheetWithList({ linesNumber: 1 });
    autofill(model, "A2", "A3");
    expect(getCellValue(model, "A3")).toBe("Loading...");
    await animationFrame(); // Await for the batch collection of missing ids
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A3")).toBe(1);
});

test("Autofill with references works like any regular function (no custom autofill)", async function () {
    const { model } = await createSpreadsheetWithList();
    setCellContent(model, "A1", '=ODOO.LIST(1, A1,"probability")');
    selectCell(model, "A1");

    model.dispatch("AUTOFILL_SELECT", { col: 0, row: 1 });
    model.dispatch("AUTOFILL");
    expect(getCellFormula(model, "A2")).toBe('=ODOO.LIST(1, A2,"probability")');
});

test("Tooltip of list formulas", async function () {
    const { model } = await createSpreadsheetWithList();

    function getTooltip(xc, isColumn) {
        return model.getters.getTooltipListFormula(getCellFormula(model, xc), isColumn);
    }

    expect(getTooltip("A3", false)).toBe("Record #2");
    expect(getTooltip("A3", true)).toBe("Foo");
    expect(getTooltip("A1", false)).toBe("Foo");
    expect(getTooltip("A1", true)).toBe("Foo");
});

test("Autofill list formula with missing listId", async function () {
    patchTranslations();
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
    expect(getListAutofillValue(model, "A1", { direction: "bottom", steps: 1 })).toBe(
        '=ODOO.LIST("1","1","date")'
    );
    expect(getListAutofillValue(model, "B1", { direction: "bottom", steps: 1 })).toBe(
        '=ODOO.LIST.HEADER("1","date")'
    );
    expect(model.getters.getTooltipListFormula(getCellFormula(model, "A1"), false)).toBe(
        "Missing list #1"
    );
    expect(model.getters.getTooltipListFormula(getCellFormula(model, "B1"), false)).toBe(
        "Missing list #1"
    );
});

test("Autofill list keeps format but neither style nor border", async function () {
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
    expect(startingCell.style).toEqual(style);
    expect(model.getters.getCellBorder({ sheetId, col, row }).left).toEqual(border.left);
    expect(startingCell.format).toBe("m/d/yyyy");

    // Check that the format of C2 has been correctly applied to C3 but not the style nor the border
    const filledCell = getCell(model, "C3");
    expect(filledCell.style).toBe(undefined);
    expect(model.getters.getCellBorder({ sheetId, col, row: row + 1 })).toBe(null);
    expect(filledCell.format).toBe("m/d/yyyy");
});
