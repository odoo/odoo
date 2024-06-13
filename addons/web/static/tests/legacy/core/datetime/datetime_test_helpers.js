/** @odoo-module alias=@web/../tests/core/datetime/datetime_test_helpers default=false */

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { localization } from "@web/core/l10n/localization";
import { ensureArray } from "@web/core/utils/arrays";
import { click, getFixture } from "../../helpers/utils";

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
    const assert = QUnit.assert;
    const fixture = getFixture();

    // Check for picker in DOM
    if (expectedParams) {
        assert.containsOnce(fixture, ".o_datetime_picker");
    } else {
        assert.containsNone(fixture, ".o_datetime_picker");
        return;
    }

    const { title, date, time } = expectedParams;

    // Title
    if (title) {
        const expectedTitle = ensureArray(title);
        assert.containsOnce(fixture, ".o_datetime_picker_header");
        assert.deepEqual(
            getTexts(".o_datetime_picker_header", "strong"),
            expectedTitle,
            `title should be "${expectedTitle.join(" - ")}"`
        );
    } else {
        assert.containsNone(fixture, ".o_datetime_picker_header");
    }

    // Time picker
    if (time) {
        assert.containsN(fixture, ".o_time_picker", time.length);
        const timePickers = select(".o_time_picker");
        for (let i = 0; i < time.length; i++) {
            const expectedTime = time[i];
            const values = select(timePickers[i], ".o_time_picker_select").map((sel) => sel.value);
            const actual = [...values.slice(0, 2).map(Number), ...values.slice(2)];
            assert.deepEqual(actual, expectedTime, `time values should be [${expectedTime}]`);
        }
    } else {
        assert.containsNone(fixture, ".o_time_picker");
    }

    // Date picker
    const datePickerEls = select(".o_date_picker");
    assert.containsN(fixture, ".o_date_picker", date.length);

    let selectedCells = 0;
    let outOfRangeCells = 0;
    let todayCells = 0;
    for (let i = 0; i < date.length; i++) {
        const { cells, daysOfWeek, weekNumbers } = date[i];
        const datePickerEl = datePickerEls[i];
        const cellEls = select(datePickerEl, ".o_date_item_cell");

        assert.strictEqual(
            cellEls.length,
            PICKER_ROWS * PICKER_COLS,
            `picker should have ${
                PICKER_ROWS * PICKER_COLS
            } cells (${PICKER_ROWS} rows and ${PICKER_COLS} columns)`
        );

        if (daysOfWeek) {
            const actualDow = getTexts(datePickerEl, ".o_day_of_week_cell");
            assert.deepEqual(
                actualDow,
                daysOfWeek,
                `picker should display the days of week: ${daysOfWeek
                    .map((dow) => `"${dow}"`)
                    .join(", ")}`
            );
        }

        if (weekNumbers) {
            assert.deepEqual(
                getTexts(datePickerEl, ".o_week_number_cell").map(Number),
                weekNumbers,
                `picker should display the week numbers (${weekNumbers.join(", ")})`
            );
        }

        // Date cells
        const expectedCells = cells.flatMap((row, rowIndex) =>
            row.map((cell, colIndex) => {
                const cellEl = cellEls[rowIndex * PICKER_COLS + colIndex];

                // Check flags
                let value = cell;
                const isSelected = Array.isArray(cell);
                if (isSelected) {
                    value = value[0];
                }
                const isToday = typeof value === "string";
                if (isToday) {
                    value = Number(value);
                }
                const isOutOfRange = value < 0;
                if (isOutOfRange) {
                    value = Math.abs(value);
                }

                // Assert based on flags
                if (isSelected) {
                    selectedCells++;
                    assert.hasClass(cellEl, "o_selected");
                }
                if (isOutOfRange) {
                    outOfRangeCells++;
                    assert.hasClass(cellEl, "o_out_of_range");
                }
                if (isToday) {
                    todayCells++;
                    assert.hasClass(cellEl, "o_today");
                }

                return value;
            })
        );

        assert.deepEqual(
            cellEls.map((cell) => Number(getTexts(cell)[0])),
            expectedCells,
            `cell content should match the expected values: [${expectedCells.join(", ")}]`
        );
    }

    assert.containsN(fixture, ".o_selected", selectedCells);
    assert.containsN(fixture, ".o_out_of_range", outOfRangeCells);
    assert.containsN(fixture, ".o_today", todayCells);
}

export function getPickerApplyButton() {
    return select(".o_datetime_picker .o_datetime_buttons .o_apply").at(0);
}

/**
 * @param {RegExp | string} expr
 */
export function getPickerCell(expr) {
    const regex = expr instanceof RegExp ? expr : new RegExp(`^${expr}$`, "i");
    const cells = select(".o_datetime_picker .o_date_item_cell").filter((cell) =>
        regex.test(getTexts(cell)[0])
    );
    return cells.length === 1 ? cells[0] : cells;
}

/**
 * @param {...(string | HTMLElement)} selectors
 * @returns {string[]}
 */
export function getTexts(...selectors) {
    return select(...selectors).map((e) => e.innerText.trim().replace(/\s+/g, " "));
}

/**
 * @param {Object} [options={}]
 * @param {boolean} [options.parse=false] whether to directly return the parsed
 *  values of the select elements
 * @returns {HTMLSelectElement[] | (number | string)[]}
 */
export function getTimePickers({ parse = false } = {}) {
    return select(".o_time_picker").map((timePickerEl) => {
        const selects = select(timePickerEl, ".o_time_picker_select");
        if (parse) {
            return selects.map((sel) => (isNaN(sel.value) ? sel.value : Number(sel.value)));
        } else {
            return selects;
        }
    });
}

/**
 * @param  {...(string | HTMLElement)} selectors
 * @returns {HTMLElement[]}
 */
const select = (...selectors) => {
    const root = selectors[0] instanceof Element ? selectors.shift() : getFixture();
    return selectors.length ? [...root.querySelectorAll(selectors.join(" "))] : [root];
};

export function useTwelveHourClockFormat() {
    const { dateFormat = "dd/MM/yyyy", timeFormat = "HH:mm:ss" } = localization;
    const twcTimeFormat = `${timeFormat.replace(/H/g, "h")} a`;
    patchWithCleanup(localization, {
        dateTimeFormat: `${dateFormat} ${twcTimeFormat}`,
        timeFormat: twcTimeFormat,
    });
}

export function zoomOut() {
    return click(getFixture(), ".o_zoom_out");
}

const PICKER_ROWS = 6;
const PICKER_COLS = 7;
