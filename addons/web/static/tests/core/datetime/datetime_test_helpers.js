import { expect } from "@odoo/hoot";
import {
    click,
    queryAll,
    queryAllTexts,
    queryAllValues,
    queryFirst,
    queryText,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

const PICKER_COLS = 7;

/**
 * @typedef {import("@web/core/datetime/datetime_picker").DateTimePickerProps} DateTimePickerProps
 */

/**
 * @param {false | {
 *  title?: string | string[],
 *  date?: {
 *      cells: (number | string | [number] | [string])[][],
 *      daysOfWeek?: string[],
 *      weekNumbers?: number[],
 *  }[],
 *  time?: ([number, number] | [number, number, "AM" | "PM"])[],
 * }} expectedParams
 */
export function assertDateTimePicker(expectedParams) {
    // Check for picker in DOM
    if (expectedParams) {
        expect(".o_datetime_picker").toHaveCount(1);
    } else {
        expect(".o_datetime_picker").toHaveCount(0);
        return;
    }

    const { title, date, time } = expectedParams;

    // Title
    if (title) {
        expect(".o_datetime_picker_header").toHaveCount(1);
        expect(".o_datetime_picker_header").toHaveText(title);
    } else {
        expect(".o_datetime_picker_header").toHaveCount(0);
    }

    // Time picker
    if (time) {
        expect(".o_time_picker").toHaveCount(time.length);
        for (let i = 0; i < time.length; i++) {
            const expectedTime = time[i];
            const values = queryAll(`.o_time_picker:nth-child(${i + 1}) .o_time_picker_select`).map(
                (sel) => sel.value
            );
            const actual = [...values.slice(0, 2).map(Number), ...values.slice(2)];
            expect(actual).toEqual(expectedTime, {
                message: `time values should be [${expectedTime}]`,
            });
        }
    } else {
        expect(".o_time_picker").toHaveCount(0);
    }

    // Date picker
    expect(".o_date_picker").toHaveCount(date.length);

    let selectedCells = 0;
    let invalidCells = 0;
    let outOfRangeCells = 0;
    let todayCells = 0;
    for (let i = 0; i < date.length; i++) {
        const { cells, daysOfWeek, weekNumbers } = date[i];
        const cellEls = queryAll(`.o_date_picker:nth-child(${i + 1}) .o_date_item_cell`);
        const pickerRows = cells.length;
        expect(cellEls.length).toBe(pickerRows * PICKER_COLS, {
            message: `picker should have ${
                pickerRows * PICKER_COLS
            } cells (${pickerRows} rows and ${PICKER_COLS} columns)`,
        });

        if (daysOfWeek) {
            const actualDow = queryAllTexts(
                `.o_date_picker:nth-child(${i + 1}) .o_day_of_week_cell`
            );
            expect(actualDow).toEqual(daysOfWeek, {
                message: `picker should display the days of week: ${daysOfWeek
                    .map((dow) => `"${dow}"`)
                    .join(", ")}`,
            });
        }

        if (weekNumbers) {
            expect(
                queryAllTexts(`.o_date_picker:nth-child(${i + 1}) .o_week_number_cell`).map(Number)
            ).toEqual(weekNumbers, {
                message: `picker should display the week numbers (${weekNumbers.join(", ")})`,
            });
        }

        // Date cells
        const expectedCells = cells.flatMap((row, rowIndex) =>
            row.map((cell, colIndex) => {
                const cellEl = cellEls[rowIndex * PICKER_COLS + colIndex];
                let value = cell;
                if (Array.isArray(cell)) {
                    // Selected
                    value = value[0];
                    selectedCells++;
                    expect(cellEl).toHaveClass("o_selected");
                }
                if (typeof value === "string") {
                    // Today
                    value = Number(value);
                    todayCells++;
                    expect(cellEl).toHaveClass("o_today");
                }
                if (value === 0) {
                    // Out of range
                    value = "";
                    outOfRangeCells++;
                    expect(cellEl).toHaveClass("o_out_of_range");
                } else if (value < 0) {
                    // Invalid
                    value = Math.abs(value);
                    invalidCells++;
                    expect(cellEl).toHaveAttribute("disabled");
                }
                return String(value);
            })
        );

        expect(cellEls.map((cell) => queryText(cell))).toEqual(expectedCells, {
            message: `cell content should match the expected values: [${expectedCells.join(", ")}]`,
        });
    }

    expect(".o_selected").toHaveCount(selectedCells);
    expect(".o_datetime_button[disabled]").toHaveCount(invalidCells);
    expect(".o_out_of_range").toHaveCount(outOfRangeCells);
    expect(".o_today").toHaveCount(todayCells);
}

/**
 * @param {RegExp | string} expr
 * @param {boolean} [inBounds=false]
 */
export function getPickerCell(expr, inBounds = false) {
    const cells = queryAll(
        `.o_datetime_picker .o_date_item_cell${
            inBounds ? ":not(.o_out_of_range)" : ""
        }:contains("/^${expr}$/")`
    );
    return cells.length === 1 ? cells[0] : cells;
}

export function getPickerApplyButton() {
    return queryFirst(".o_datetime_picker .o_datetime_buttons .o_apply");
}

export async function zoomOut() {
    click(".o_zoom_out");
    await animationFrame();
}

export function getTimePickers({ parse = false } = {}) {
    return queryAll(".o_time_picker").map((timePickerEl) => {
        if (parse) {
            return queryAllValues(".o_time_picker_select", { root: timePickerEl });
        }
        return queryAll(".o_time_picker_select", { root: timePickerEl });
    });
}
