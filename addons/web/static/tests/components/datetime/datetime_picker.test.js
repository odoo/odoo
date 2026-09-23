// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { click, hover, queryAll, queryAllTexts, resize } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { Component, onRendered, useState, xml } from "@odoo/owl";
import {
    assertDateTimePicker,
    editTime,
    getPickerCell,
} from "@web/../tests/components/datetime/datetime_test_helpers";
import {
    defineParams,
    makeMockEnv,
    mountWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { DateTimePicker } from "@web/components/datetime/datetime_picker";
import { luxon } from "@web/core/l10n/luxon";
import { ensureArray } from "@web/core/utils/collections/arrays";

const { DateTime } = luxon;

/** @param {import("@web/components/datetime/datetime_picker").DateTimePickerProps["value"]} value */
const formatForStep = (value) =>
    ensureArray(value)
        .map((val) => (val ? val.toISO().split(".")[0] : ""))
        .join(",");

/** @param {any} value */
const pad2 = (value) => String(value).padStart(2, "0");

/**
 * @template {any} [T=number]
 * @param {number} length
 * @param {(index: number) => T} mapping
 */
const range = (length, mapping) => [...Array(length)].map((_, i) => mapping(i));

const MINUTES = range(60, (i) => i).filter((i) => i % 15 === 0);
const TIME_OPTIONS = range(24, String).flatMap((h) =>
    MINUTES.map((m) => `${h}:${pad2(m)}`),
);

defineParams({
    lang_parameters: {
        date_format: "%d/%m/%Y",
        time_format: "%H:%M:%S",
    },
});

beforeEach(() => mockDate("2023-04-25T12:45:01"));

test("default params", async () => {
    await mountWithCleanup(DateTimePicker);

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });

    await click(".o_time_picker_input");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(
        TIME_OPTIONS,
    );
    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "8",
    });
});

test("minDate: correct days/month/year/decades are disabled", async () => {
    serverState.lang = "en-US";
    await makeMockEnv();

    await mountWithCleanup(DateTimePicker, {
        props: {
            minDate: DateTime.fromISO("2023-04-20T00:00:00.000"),
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [-26, -27, -28, -29, -30, -31, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });

    await click(".o_time_picker_input");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(
        TIME_OPTIONS,
    );

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("2023");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual(["Jan", "Feb", "Mar"]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual([
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]);
    expect(".o_date_item_cell.o_today").toHaveText("Apr");

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("2019 - 2030");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "2019",
        "2020",
        "2021",
        "2022",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual([
        "2023",
        "2024",
        "2025",
        "2026",
        "2027",
        "2028",
        "2029",
        "2030",
    ]);
    expect(".o_date_item_cell.o_today").toHaveText("2023");

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("1990 - 2100");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "1990",
        "2000",
        "2010",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual([
        "2020",
        "2030",
        "2040",
        "2050",
        "2060",
        "2070",
        "2080",
        "2090",
        "2100",
    ]);
    expect(".o_date_item_cell.o_today").toHaveText("2020");

    await click(".o_today");
    await animationFrame();
    await click(".o_today");
    await animationFrame();
    await click(".o_today");
    await animationFrame();

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [-26, -27, -28, -29, -30, -31, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });
});

test("maxDate: correct days/month/year/decades are disabled", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            maxDate: DateTime.fromISO("2023-04-28T00:00:00.000"),
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, -1, -2, -3, -4, -5, -6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });

    await click(".o_time_picker_input");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(
        TIME_OPTIONS,
    );

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("2023");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual([
        "Jan",
        "Feb",
        "Mar",
        "Apr",
    ]);
    expect(".o_date_item_cell.o_today").toHaveText("Apr");

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("2019 - 2030");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "2024",
        "2025",
        "2026",
        "2027",
        "2028",
        "2029",
        "2030",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual([
        "2019",
        "2020",
        "2021",
        "2022",
        "2023",
    ]);
    expect(".o_date_item_cell.o_today").toHaveText("2023");

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("1990 - 2100");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "2030",
        "2040",
        "2050",
        "2060",
        "2070",
        "2080",
        "2090",
        "2100",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual([
        "1990",
        "2000",
        "2010",
        "2020",
    ]);
    expect(".o_date_item_cell.o_today").toHaveText("2020");

    await click(".o_today");
    await animationFrame();
    await click(".o_today");
    await animationFrame();
    await click(".o_today");
    await animationFrame();

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, -1, -2, -3, -4, -5, -6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });
});

test("min+max date: correct days/month/year/decades are disabled", async () => {
    serverState.lang = "en-US";
    await makeMockEnv();

    await mountWithCleanup(DateTimePicker, {
        props: {
            minDate: DateTime.fromISO("2023-04-20T00:00:00.000"),
            maxDate: DateTime.fromISO("2023-04-28T00:00:00.000"),
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [-26, -27, -28, -29, -30, -31, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, -1, -2, -3, -4, -5, -6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });

    await click(".o_time_picker_input");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(
        TIME_OPTIONS,
    );

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("2023");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "Jan",
        "Feb",
        "Mar",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual(["Apr"]);
    expect(".o_date_item_cell.o_today").toHaveText("Apr");

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("2019 - 2030");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "2019",
        "2020",
        "2021",
        "2022",
        "2024",
        "2025",
        "2026",
        "2027",
        "2028",
        "2029",
        "2030",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual(["2023"]);
    expect(".o_date_item_cell.o_today").toHaveText("2023");

    await click(".o_zoom_out");
    await animationFrame();

    expect(".o_datetime_picker_header").toHaveText("1990 - 2100");
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual([
        "1990",
        "2000",
        "2010",
        "2030",
        "2040",
        "2050",
        "2060",
        "2070",
        "2080",
        "2090",
        "2100",
    ]);
    expect(queryAllTexts(".o_date_item_cell:not([disabled])")).toEqual(["2020"]);
    expect(".o_date_item_cell.o_today").toHaveText("2020");

    await click(".o_today");
    await animationFrame();
    await click(".o_today");
    await animationFrame();
    await click(".o_today");
    await animationFrame();

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [-26, -27, -28, -29, -30, -31, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, -1, -2, -3, -4, -5, -6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });
});

test("twelve-hour clock with non-null focus date index", async () => {
    defineParams({
        lang_parameters: {
            time_format: "hh:mm:ss a",
        },
    });

    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => {
                expect.step(formatForStep(value));
            },
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 45 }),
                DateTime.fromObject({ day: 23, hour: 11, minute: 15 }),
            ],
            focusedDateIndex: 1,
        },
    });

    await editTime("07:15am");
    expect.verifySteps(["2023-04-20T08:45:00,2023-04-23T07:15:00"]);
});

test("twelve-hour clock", async () => {
    defineParams({
        lang_parameters: {
            time_format: "hh:mm:ss a",
        },
    });

    await mountWithCleanup(DateTimePicker);

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["1:00pm"],
    });

    const times = [];
    for (const meridiem of ["am", "pm"]) {
        for (const h of [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]) {
            for (const m of ["00", "15", "30", "45"]) {
                times.push(`${h}:${m}${meridiem}`);
            }
        }
    }
    await click(".o_time_picker_input");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(
        times,
    );
});

test("hide time picker", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            type: "date",
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
    });
});

test("focus is adjusted to selected date", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: DateTime.fromObject({ month: 5, day: 29, hour: 23, minute: 55 }),
        },
    });

    assertDateTimePicker({
        title: "May 2023",
        date: [
            {
                cells: [
                    [30, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, [29], 30, 31, 1, 2, 3],
                    [4, 5, 6, 7, 8, 9, 10],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [18, 19, 20, 21, 22, 23],
            },
        ],
        time: ["23:55"],
    });
});

test("next month and previous month", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            type: "date",
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
    });

    await click(".o_previous");
    await animationFrame();

    assertDateTimePicker({
        title: "March 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 1, 2, 3, 4],
                    [5, 6, 7, 8, 9, 10, 11],
                    [12, 13, 14, 15, 16, 17, 18],
                    [19, 20, 21, 22, 23, 24, 25],
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [9, 10, 11, 12, 13, 14],
            },
        ],
    });

    await click(".o_next");
    await animationFrame();

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
    });

    await click(".o_next");
    await animationFrame();

    assertDateTimePicker({
        title: "May 2023",
        date: [
            {
                cells: [
                    [30, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 1, 2, 3],
                    [4, 5, 6, 7, 8, 9, 10],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [18, 19, 20, 21, 22, 23],
            },
        ],
    });
});

test.tags("desktop");
test("range value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 5, hour: 17, minute: 18 }),
                DateTime.fromObject({ month: 5, day: 18, hour: 5, minute: 25 }),
            ],
            range: true,
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, [5], [6], [7], [8]],
                    [[9], [10], [11], [12], [13], [14], [15]],
                    [[16], [17], [18], [19], [20], [21], [22]],
                    [[23], [24], ["25"], [26], [27], [28], [29]],
                    [[30], [1], [2], [3], [4], [5], [6]],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["17:18", "5:25"],
    });

    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_option")).toEqual(TIME_OPTIONS);

    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_option")).toEqual(TIME_OPTIONS);

    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "8",
    });
});

test("range value on small device", async () => {
    await resize({ width: 300 });

    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ hour: 9, minute: 30 }),
                DateTime.fromObject({ hour: 21, minute: 5 }),
            ],
            range: true,
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, ["25"], 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["9:30", "21:05"],
    });

    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_option")).toEqual(TIME_OPTIONS);

    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    expect(queryAllTexts(".o_time_picker_option")).toEqual(TIME_OPTIONS);

    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "8",
    });
});

test.tags("desktop");
test("range value, previous month", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [false, false],
            range: true,
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00", "14:00"],
    });

    await click(".o_previous");
    await animationFrame();

    assertDateTimePicker({
        title: "March 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 1, 2, 3, 4],
                    [5, 6, 7, 8, 9, 10, 11],
                    [12, 13, 14, 15, 16, 17, 18],
                    [19, 20, 21, 22, 23, 24, 25],
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [9, 10, 11, 12, 13, 14],
            },
        ],
        time: ["13:00", "14:00"],
    });
});

test("days of week narrow format", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            daysOfWeekFormat: "narrow",
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: ["13:00"],
    });
});

test("different rounding", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            rounding: 10,
        },
    });

    await editTime("10:16");
    expect(".o_time_picker_input").toHaveValue("10:20");
});

test("rounding=0 enables seconds", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            rounding: 0,
        },
    });

    expect(".o_time_picker_input").toHaveValue("13:00:00");
});

test("no value, select date without handler", async () => {
    await mountWithCleanup(DateTimePicker);

    await click(getPickerCell("12"));
    await animationFrame();

    expect.verifySteps([]);
});

test("no value, select date", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("5"));
    await animationFrame();
    await click(getPickerCell("12"));
    await animationFrame();

    expect.verifySteps(["2023-04-05T13:00:00", "2023-04-12T13:00:00"]);
});

test("no value, select time", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await editTime("18:05");
    await animationFrame();

    expect.verifySteps(["2023-04-25T18:05:00"]);
});

test("minDate with time: selecting out-of-range and in-range times", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
            minDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
        },
    });

    await editTime("15:00");
    await animationFrame();
    expect.verifySteps([]);

    await editTime("16:00");
    await animationFrame();
    expect.verifySteps(["2023-04-25T16:00:00"]);
});

test("maxDate with time: selecting out-of-range and in-range times", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
            maxDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
        },
    });

    await editTime("17:00");
    await animationFrame();
    expect.verifySteps([]);

    await editTime("16:00");
    await animationFrame();
    expect.verifySteps(["2023-04-25T16:00:00"]);
});

test("max and min date with time: selecting out-of-range and in-range times", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
            minDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
            maxDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
        },
    });

    await editTime("15:00");
    await editTime("17:00");
    await animationFrame();
    expect.verifySteps([]);

    await editTime("16:00");
    await animationFrame();
    expect.verifySteps(["2023-04-25T16:00:00"]);
});

test("max and min date with time: selecting invalid minutes and making it valid by selecting hours", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
            minDate: DateTime.fromISO("2023-04-25T16:10:00.000"),
            maxDate: DateTime.fromISO("2023-04-25T16:50:00.000"),
        },
    });

    await editTime("13:30");
    await animationFrame();
    expect.verifySteps([]);

    await editTime("16:30");
    await animationFrame();
    expect.verifySteps(["2023-04-25T16:30:00"]);
});

test("max and min date with time: valid time on invalid day becomes valid when selecting day", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
            minDate: DateTime.fromISO("2023-04-24T16:10:00.000"),
            maxDate: DateTime.fromISO("2023-04-24T16:50:00.000"),
        },
    });

    await editTime("16:30");
    await animationFrame();
    expect.verifySteps([]);

    await click(getPickerCell("24"));
    await animationFrame();
    expect.verifySteps(["2023-04-24T16:30:00"]);
});

test("custom invalidity function", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            type: "date",
            isDateValid: (/** @type {any} */ date) => date.weekday <= 5,
        },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [-26, 27, 28, 29, 30, 31, -1],
                    [-2, 3, 4, 5, 6, 7, -8],
                    [-9, 10, 11, 12, 13, 14, -15],
                    [-16, 17, 18, 19, 20, 21, -22],
                    [-23, 24, "25", 26, 27, 28, -29],
                    [-30, 1, 2, 3, 4, 5, -6],
                ],
            },
        ],
    });
});

test("custom date cell class function", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            type: "date",
            dayCellClass: (/** @type {any} */ date) =>
                date.weekday >= 6 ? "o_weekend" : "",
        },
    });

    expect(queryAllTexts(".o_weekend")).toEqual([
        "26",
        "1",
        "2",
        "8",
        "9",
        "15",
        "16",
        "22",
        "23",
        "29",
        "30",
        "6",
    ]);
});

test("single value, select date", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: DateTime.fromObject({ day: 30, hour: 8, minute: 43 }),
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("5"));
    await animationFrame();
    expect.verifySteps(["2023-04-05T08:43:00"]);
});

test("single value, select time", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: DateTime.fromObject({ day: 30, hour: 8, minute: 43 }),
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await editTime("18:05");
    await animationFrame();
    expect.verifySteps(["2023-04-30T18:05:00"]);
});

test("single value, select time in twelve-hour clock format", async () => {
    defineParams({
        lang_parameters: {
            time_format: "hh:mm:ss a",
        },
    });
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: DateTime.fromObject({ day: 30, hour: 8, minute: 43 }),
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await editTime("7:05PM");
    await animationFrame();
    expect.verifySteps(["2023-04-30T19:05:00"]);
});

test("range value, select date for first value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("5"));
    await animationFrame();
    expect.verifySteps(["2023-04-05T08:43:00,2023-04-23T17:16:00"]);
});

test("range value, select time for first value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await editTime("18:05");
    await animationFrame();
    expect.verifySteps(["2023-04-20T18:05:00,2023-04-23T17:16:00"]);
});

test.tags("desktop");
test("range value, select date for second value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 1,
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("21"));
    await animationFrame();
    expect.verifySteps(["2023-04-20T08:43:00,2023-04-21T17:16:00"]);
});

test("range value, select time for second value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 1,
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await editTime("18:05", 1);
    await animationFrame();
    expect.verifySteps(["2023-04-20T08:43:00,2023-04-23T18:05:00"]);
});

test.tags("desktop");
test("range value, select date for second value before first value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 1,
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("19"));
    await animationFrame();
    expect.verifySteps(["2023-04-20T08:43:00,2023-04-19T17:16:00"]);
});

test("range value, select date for first value after second value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 0,
            onSelect: (/** @type {any} */ value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("27", true));
    await animationFrame();
    expect.verifySteps(["2023-04-27T08:43:00,2023-04-23T17:16:00"]);
});

test("focus proper month when changing props out of current month", async () => {
    class Parent extends Component {
        static template = xml`<DateTimePicker value="this.state.current"/>`;
        static components = { DateTimePicker };
        static props = ["*"];
        setup() {
            this.state = useState({
                current: DateTime.now(),
            });
        }
    }

    const parent = await mountWithCleanup(Parent);

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, ["25"], 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
            },
        ],
        time: ["13:45"],
    });

    parent.state.current = DateTime.fromObject({
        month: 5,
        day: 1,
        hour: 17,
        minute: 16,
    });
    await animationFrame();

    assertDateTimePicker({
        title: "May 2023",
        date: [
            {
                cells: [
                    [30, [1], 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 1, 2, 3],
                    [4, 5, 6, 7, 8, 9, 10],
                ],
                daysOfWeek: ["", "S", "M", "T", "W", "T", "F", "S"],
            },
        ],
        time: ["17:16"],
    });
});

test("disable show week numbers", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: { showWeekNumbers: false },
    });

    assertDateTimePicker({
        title: "April 2023",
        date: [
            {
                cells: [
                    [26, 27, 28, 29, 30, 31, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 1, 2, 3, 4, 5, 6],
                ],
                daysOfWeek: ["S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [],
            },
        ],
        time: ["13:00"],
    });

    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "7",
    });
});

test("grid is reused on hover, rebuilt on focus change", async () => {
    const picker = await mountWithCleanup(DateTimePicker, {
        props: { value: DateTime.fromObject({ day: 5 }) },
    });
    const itemsBefore = picker.items;
    const titleBefore = picker.title;
    expect(Array.isArray(itemsBefore)).toBe(true);

    picker.state.hoveredDate = DateTime.fromObject({ day: 20 });
    await animationFrame();
    expect(picker.items).toBe(itemsBefore);
    expect(picker.title).toBe(titleBefore);

    picker.state.focusDate = picker.state.focusDate.plus({ month: 1 });
    await animationFrame();
    expect(picker.items).not.toBe(itemsBefore);
});

test("dynamic date<->datetime switch recomputes min/max with the NEW type", async () => {
    class Parent extends Component {
        static components = { DateTimePicker };
        static props = {};
        static template = xml`
            <DateTimePicker
                type="this.state.type"
                value="this.value"
                maxDate="this.maxDate"
                onSelect.bind="this.onSelect"
            />
        `;

        setup() {
            this.state = useState({ type: "date" });
            this.value = DateTime.fromISO("2023-04-25T09:00:00.000");
            this.maxDate = DateTime.fromISO("2023-04-25T09:30:00.000");
        }

        onSelect(/** @type {any} */ value) {
            expect.step(formatForStep(value));
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(".o_time_picker").toHaveCount(0);

    parent.state.type = "datetime";
    await animationFrame();
    expect(".o_time_picker").toHaveCount(1);

    await editTime("13:00");
    await animationFrame();
    expect.verifySteps([]);

    await editTime("09:15");
    await animationFrame();
    expect.verifySteps(["2023-04-25T09:15:00"]);
});

test.tags("desktop");
test("range with no end: end time defaults to start + 1h, not to the current time", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [DateTime.fromObject({ day: 5, hour: 3, minute: 0 }), false],
            range: true,
        },
    });

    expect(".o_time_picker_input:eq(0)").toHaveValue("3:00");
    expect(".o_time_picker_input:eq(1)").toHaveValue("4:00");
});

test.tags("desktop");
test("range with no end: start at 23h clamps the end time instead of wrapping", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [DateTime.fromObject({ day: 5, hour: 23, minute: 0 }), false],
            range: true,
        },
    });

    expect(".o_time_picker_input:eq(1)").toHaveValue("23:00");
});

test("grid refreshes when isDateValid / dayCellClass change their answer", async () => {
    const rules = { blockedWeekday: null };
    const picker = await mountWithCleanup(DateTimePicker, {
        props: {
            type: "date",
            isDateValid: (/** @type {any} */ date) =>
                date.weekday !== rules.blockedWeekday,
            dayCellClass: (/** @type {any} */ date) =>
                date.weekday === rules.blockedWeekday ? "o_blocked" : "",
        },
    });
    expect(".o_date_item_cell[disabled]").toHaveCount(0);
    expect(".o_blocked").toHaveCount(0);

    rules.blockedWeekday = 6;
    picker.render();
    await animationFrame();

    expect(".o_date_item_cell[disabled]").toHaveCount(6);
    expect(".o_blocked").toHaveCount(6);
});

test.tags("desktop");
test("hovering a day of a single-date picker renders nothing", async () => {
    let renders = 0;
    class Probe extends DateTimePicker {
        setup() {
            super.setup();
            onRendered(() => renders++);
        }
    }
    await mountWithCleanup(Probe, { props: { type: "date" } });
    renders = 0;
    await hover(getPickerCell("10"));
    await hover(getPickerCell("11"));
    await animationFrame();
    expect(renders).toBe(0);
});

test.tags("desktop");
test("hovering re-asks the day callbacks without rebuilding the grid", async () => {
    /** @type {any[]} */
    const asked = [];
    await mountWithCleanup(DateTimePicker, {
        props: {
            type: "date",
            range: true,
            value: [DateTime.fromObject({ day: 5 }), false],
            focusedDateIndex: 1,
            dayCellClass: (/** @type {any} */ date) => {
                asked.push(date);
                return "";
            },
        },
    });

    const firstPass = asked.length;
    expect(firstPass).toBeGreaterThan(41);

    await hover(getPickerCell("10"));
    await animationFrame();

    expect(asked.length).toBeGreaterThan(firstPass);
    expect(asked[firstPass]).toBe(asked[0]);
    expect(asked[firstPass + 41]).toBe(asked[41]);
});

test("without isDateValid every in-month day stays selectable", async () => {
    await mountWithCleanup(DateTimePicker, { props: { type: "date" } });

    const cells = queryAll(".o_date_item_cell:not(.o_out_of_range)");
    expect(cells.length).toBeGreaterThan(20);
    expect(cells.filter((cell) => cell.matches(":disabled")).length).toBe(0);
    expect(".o_date_item_cell:not(.o_out_of_range).opacity-50").toHaveCount(0);
});

test("the day grid restates today after the clock crosses midnight", async () => {
    mockDate("2023-04-25T12:00:00");
    const picker = await mountWithCleanup(DateTimePicker, {
        props: { type: "date" },
    });
    expect(queryAllTexts(".o_today")).toEqual(["25"]);

    mockDate("2023-04-27T12:00:00");
    picker.render(true);
    await animationFrame();

    expect(queryAllTexts(".o_today")).toEqual(["27"]);
});

test("a render that does not move the value leaves the browsed month alone", async () => {
    class Parent extends Component {
        static template = xml`
            <span class="tick" t-out="this.state.tick"/>
            <DateTimePicker value="this.state.value" onSelect="() => {}" type="'date'"/>`;
        static components = { DateTimePicker };
        static props = [];
        state = useState({ value: DateTime.fromISO("2023-04-25"), tick: 0 });
    }
    const parent = await mountWithCleanup(Parent);
    expect(".o_datetime_picker_header").toHaveText(/April 2023/i);

    await click(".o_next");
    await animationFrame();
    expect(".o_datetime_picker_header").toHaveText(/May 2023/i);

    parent.state.tick++;
    await animationFrame();
    expect(".o_datetime_picker_header").toHaveText(/May 2023/i);
});

test("a value moving to another month takes the browsed month with it", async () => {
    class Parent extends Component {
        static template = xml`<DateTimePicker value="this.state.value" onSelect="() => {}" type="'date'"/>`;
        static components = { DateTimePicker };
        static props = [];
        state = useState({ value: DateTime.fromISO("2023-04-25") });
    }
    const parent = await mountWithCleanup(Parent);
    await click(".o_next");
    await animationFrame();
    expect(".o_datetime_picker_header").toHaveText(/May 2023/i);

    parent.state.value = DateTime.fromISO("2023-07-14");
    await animationFrame();
    expect(".o_datetime_picker_header").toHaveText(/July 2023/i);
});
