import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAllTexts, resize, select } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { ensureArray } from "@web/core/utils/arrays";
import { defineParams, mountWithCleanup, makeMockEnv, serverState } from "@web/../tests/web_test_helpers";
import { assertDateTimePicker, getPickerCell } from "../../datetime/datetime_test_helpers";

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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(12, (i) => pad2(i * 5))
    );
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
                    [0, 0, 0, 0, 0, 0, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(12, (i) => pad2(i * 5))
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
                    [0, 0, 0, 0, 0, 0, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(12, (i) => pad2(i * 5))
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
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
                    [0, 0, 0, 0, 0, 0, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(12, (i) => pad2(i * 5))
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
                    [0, 0, 0, 0, 0, 0, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                    [-9, -10, -11, -12, -13, -14, -15],
                    [-16, -17, -18, -19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, -29],
                    [-30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
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
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 11, minute: 16 }),
            ],
            focusedDateIndex: 1,
        },
    });

    await select("7", { target: ".o_time_picker_select:eq(0)" });
    expect.verifySteps(["2023-04-20T08:43:00,2023-04-23T07:16:00"]);
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[1, 0, "PM"]],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual([
        "12",
        ...range(12, String).slice(1),
    ]);
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(12, (i) => pad2(i * 5))
    );
    expect(queryAllTexts(".o_time_picker_select:eq(2) option")).toEqual(["AM", "PM"]);
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
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
                    [0, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, [29], 30, 31, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [18, 19, 20, 21, 22],
            },
        ],
        time: [[23, 55]],
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
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
                    [0, 0, 0, 1, 2, 3, 4],
                    [5, 6, 7, 8, 9, 10, 11],
                    [12, 13, 14, 15, 16, 17, 18],
                    [19, 20, 21, 22, 23, 24, 25],
                    [26, 27, 28, 29, 30, 31, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [9, 10, 11, 12, 13],
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
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
                    [0, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [18, 19, 20, 21, 22],
            },
        ],
    });
});

test.tags("desktop");
test("additional month, hide time picker", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ hour: 9, minute: 36 }),
                DateTime.fromObject({ hour: 21, minute: 5 }),
            ],
            range: true,
            type: "date",
        },
    });

    assertDateTimePicker({
        title: "April 2023\nMay 2023",
        date: [
            {
                cells: [
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, ["25"], 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
            {
                cells: [
                    [0, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
    });
});

test.tags("desktop");
test("additional month, empty range value", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [null, null],
            range: true,
        },
    });

    assertDateTimePicker({
        title: "April 2023\nMay 2023",
        date: [
            {
                cells: [
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
            {
                cells: [
                    [0, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [
            [13, 0],
            [14, 0],
        ],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(12, (i) => pad2(i * 5))
    );

    expect(queryAllTexts(".o_time_picker_select:eq(2) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(3) option")).toEqual(
        range(12, (i) => pad2(i * 5))
    );
    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "7",
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
        title: "April 2023\nMay 2023",
        date: [
            {
                cells: [
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, [5], [6], [7], [8]],
                    [[9], [10], [11], [12], [13], [14], [15]],
                    [[16], [17], [18], [19], [20], [21], [22]],
                    [[23], [24], ["25"], [26], [27], [28], [29]],
                    [[30], 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
            {
                cells: [
                    [0, [1], [2], [3], [4], [5], [6]],
                    [[7], [8], [9], [10], [11], [12], [13]],
                    [[14], [15], [16], [17], [18], 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [
            [17, 0],
            [5, 25],
        ],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    const expectedMinutes = range(12, (i) => pad2(i * 5));
    expectedMinutes.unshift("");
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(expectedMinutes);

    expect(queryAllTexts(".o_time_picker_select:eq(2) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(3) option")).toEqual(
        range(12, (i) => pad2(i * 5))
    );

    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "7",
    });
});

test("range value on small device", async () => {
    await resize({ width: 300 });

    await mountWithCleanup(DateTimePicker, {
        props: {
            value: [
                DateTime.fromObject({ hour: 9, minute: 36 }),
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, ["25"], 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [
            [9, 0],
            [21, 5],
        ],
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    const expectedMinutes = range(12, (i) => pad2(i * 5));
    expectedMinutes.unshift("");
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(expectedMinutes);

    expect(queryAllTexts(".o_time_picker_select:eq(2) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(3) option")).toEqual(
        range(12, (i) => pad2(i * 5))
    );

    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "7",
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
        title: "April 2023\nMay 2023",
        date: [
            {
                cells: [
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
            {
                cells: [
                    [0, 1, 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [
            [13, 0],
            [14, 0],
        ],
    });

    await click(".o_previous");
    await animationFrame();

    assertDateTimePicker({
        title: "March 2023\nApril 2023",
        date: [
            {
                cells: [
                    [0, 0, 0, 1, 2, 3, 4],
                    [5, 6, 7, 8, 9, 10, 11],
                    [12, 13, 14, 15, 16, 17, 18],
                    [19, 20, 21, 22, 23, 24, 25],
                    [26, 27, 28, 29, 30, 31, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
            {
                cells: [
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [
            [13, 0],
            [14, 0],
        ],
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "S", "M", "T", "W", "T", "F", "S"],
                weekNumbers: [13, 14, 15, 16, 17, 18],
            },
        ],
        time: [[13, 0]],
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

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(
        range(6, (i) => pad2(i * 10))
    );
});

test("rounding=0 enables seconds picker", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            rounding: 0,
        },
    });

    expect(queryAllTexts(".o_time_picker_select:eq(0) option")).toEqual(range(24, String));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(range(60, (i) => pad2(i)));
    expect(queryAllTexts(".o_time_picker_select:eq(1) option")).toEqual(range(60, (i) => pad2(i)));
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

    await select("18", { target: ".o_time_picker_select:eq(0)" });
    await select("5", { target: ".o_time_picker_select:eq(1)" });
    await animationFrame();

    expect.verifySteps(["2023-04-25T18:00:00", "2023-04-25T18:05:00"]);
});

test("minDate with time: selecting out-of-range and in-range times", async () => {
    await mountWithCleanup(DateTimePicker, {
        props: {
            onSelect: (value) => expect.step(formatForStep(value)),
            minDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
        },
    });

    await select("15", { target: ".o_time_picker_select:eq(0)" });
    await animationFrame();
    expect.verifySteps([]);

    await select("16", { target: ".o_time_picker_select:eq(0)" });
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

    await select("17", { target: ".o_time_picker_select:eq(0)" });
    await animationFrame();
    expect.verifySteps([]);

    await select("16", { target: ".o_time_picker_select:eq(0)" });
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

    await select("15", { target: ".o_time_picker_select:eq(0)" });
    await select("17", { target: ".o_time_picker_select:eq(0)" });
    await animationFrame();
    expect.verifySteps([]);

    await select("16", { target: ".o_time_picker_select:eq(0)" });
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

    await select("13", { target: ".o_time_picker_select:eq(0)" });
    await select("30", { target: ".o_time_picker_select:eq(1)" });
    await animationFrame();
    expect.verifySteps([]);

    await select("16", { target: ".o_time_picker_select:eq(0)" });
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

    await select("16", { target: ".o_time_picker_select:eq(0)" });
    await select("30", { target: ".o_time_picker_select:eq(1)" });
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
                    [0, 0, 0, 0, 0, 0, -1],
                    [-2, 3, 4, 5, 6, 7, -8],
                    [-9, 10, 11, 12, 13, 14, -15],
                    [-16, 17, 18, 19, 20, 21, -22],
                    [-23, 24, "25", 26, 27, 28, -29],
                    [-30, 0, 0, 0, 0, 0, 0],
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

    await select("18", { target: ".o_time_picker_select:eq(0)" });
    await select("5", { target: ".o_time_picker_select:eq(1)" });
    await animationFrame();
    expect.verifySteps(["2023-04-30T18:43:00", "2023-04-30T18:05:00"]);
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

    await select("7", { target: ".o_time_picker_select:eq(0)" });
    await select("5", { target: ".o_time_picker_select:eq(1)" });
    await select("PM", { target: ".o_time_picker_select:eq(2)" });
    await animationFrame();
    expect.verifySteps(["2023-04-30T07:43:00", "2023-04-30T07:05:00", "2023-04-30T19:05:00"]);
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

    await select("18", { target: ".o_time_picker_select:eq(0)" });
    await select("5", { target: ".o_time_picker_select:eq(1)" });
    await animationFrame();
    expect.verifySteps([
        "2023-04-20T18:43:00,2023-04-23T17:16:00",
        "2023-04-20T18:05:00,2023-04-23T17:16:00",
    ]);
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

    await click(getPickerCell("21").at(0));
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

    await select("18", { target: ".o_time_picker_select:eq(2)" });
    await select("5", { target: ".o_time_picker_select:eq(3)" });
    await animationFrame();
    expect.verifySteps([
        "2023-04-20T08:43:00,2023-04-23T18:16:00",
        "2023-04-20T08:43:00,2023-04-23T18:05:00",
    ]);
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

    await click(getPickerCell("19").at(0));
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

    await click(getPickerCell("27"));
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, ["25"], 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [[13, 45]],
    });

    parent.state.current = DateTime.fromObject({ month: 5, day: 1, hour: 17, minute: 16 });
    await animationFrame();

    assertDateTimePicker({
        title: "May 2023",
        date: [
            {
                cells: [
                    [0, [1], 2, 3, 4, 5, 6],
                    [7, 8, 9, 10, 11, 12, 13],
                    [14, 15, 16, 17, 18, 19, 20],
                    [21, 22, 23, 24, 25, 26, 27],
                    [28, 29, 30, 31, 0, 0, 0],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            },
        ],
        time: [[17, 0]],
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
                    [0, 0, 0, 0, 0, 0, 1],
                    [2, 3, 4, 5, 6, 7, 8],
                    [9, 10, 11, 12, 13, 14, 15],
                    [16, 17, 18, 19, 20, 21, 22],
                    [23, 24, "25", 26, 27, 28, 29],
                    [30, 0, 0, 0, 0, 0, 0],
                ],
                daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [],
            },
        ],
        time: [[13, 0]],
    });

    expect(".o_datetime_picker").toHaveStyle({
        "--DateTimePicker__Day-template-columns": "7",
    });
});
