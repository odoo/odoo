import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAllTexts, resize } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { ensureArray } from "@web/core/utils/arrays";
import {
    defineParams,
    mountWithCleanup,
    makeMockEnv,
    serverState,
} from "@web/../tests/web_test_helpers";
import {
    assertDateTimePicker,
    getPickerCell,
    editTime,
} from "../../datetime/datetime_test_helpers";

const { DateTime } = luxon;

/**
 * @param {DateTimePickerProps["value"]} value
 */
const formatForStep = (value) =>
    ensureArray(value)
        .map((val) => val.toISO().split(".")[0])
        .join(",");

/**
 * @param {any} value
 */
const pad2 = (value) => String(value).padStart(2, "0");

/**
 * @template {any} [T=number]
 * @param {number} length
 * @param {(index: number) => T} mapping
 */
const range = (length, mapping) => [...Array(length)].map((_, i) => mapping(i));

const MINUTES = range(60, (i) => i).filter((i) => i % 15 === 0);
const TIME_OPTIONS = range(24, String).flatMap((h) => MINUTES.map((m) => `${h}:${pad2(m)}`));

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
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(TIME_OPTIONS);
    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "8",
    });
});

test("minDate: correct days/month/year/decades are disabled", async () => {
    serverState.lang = "en-US";
    // necessary to configure the lang before minDate/maxDate are created
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
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(TIME_OPTIONS);

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
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual(["2019", "2020", "2021", "2022"]);
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
    expect(queryAllTexts(".o_date_item_cell[disabled]")).toEqual(["1990", "2000", "2010"]);
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
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(TIME_OPTIONS);

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
    // necessary to configure the lang before minDate/maxDate are created
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
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(TIME_OPTIONS);

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
    // Test the case when we have focusDateIndex != 0
    defineParams({
        lang_parameters: {
            time_format: "hh:mm:ss a",
        },
    });

    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (value) => {
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
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(times);
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

//-------------------------------------------------------------------------
// Props and interactions
//-------------------------------------------------------------------------

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

    expect.verifySteps([]); // This test just asserts that nothing happens
});

test("no value, select date", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
        },
    });

    await editTime("18:05");
    await animationFrame();

    expect.verifySteps(["2023-04-25T18:05:00"]);
});

test("minDate with time: selecting out-of-range and in-range times", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            // make weekends invalid
            isDateValid: (date) => date.weekday <= 5,
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
            // give special class to weekends
            dayCellClass: (date) => (date.weekday >= 6 ? "o_weekend" : ""),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            // focusedDateIndex is implicitly 0
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
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
            onSelect: (value) => expect.step(formatForStep(value)),
        },
    });

    await click(getPickerCell("27", true));
    await animationFrame();
    expect.verifySteps(["2023-04-27T08:43:00,2023-04-23T17:16:00"]);
});

test("focus proper month when changing props out of current month", async () => {
    class Parent extends Component {
        static template = xml`<DateTimePicker value="state.current"/>`;
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

    parent.state.current = DateTime.fromObject({ month: 5, day: 1, hour: 17, minute: 16 });
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
