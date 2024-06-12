/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { click, editSelect, getFixture, mount, patchDate } from "@web/../tests/helpers/utils";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { registry } from "@web/core/registry";
import { ensureArray } from "@web/core/utils/arrays";
import {
    assertDateTimePicker,
    getPickerCell,
    getTexts,
    getTimePickers,
    useTwelveHourClockFormat,
} from "./datetime_test_helpers";
import { Component, useState, xml } from "@odoo/owl";
import { nextTick } from "../../helpers/utils";

const { DateTime } = luxon;

/**
 * @typedef {import("@web/core/datetime/datetime_picker").DateTimePickerProps} DateTimePickerProps
 */

/**
 * @param {DateTimePickerProps["value"]} value
 */
const formatForStep = (value) =>
    ensureArray(value)
        .map((val) => val.toISO().split(".")[0])
        .join(",");

/**
 * @param {DateTimePickerProps} [props]
 */
const mountPicker = (props) => mount(DateTimePicker, getFixture(), { env, props });

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

let env;
let isSmall;
const serviceRegistry = registry.category("services");

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(async () => {
        patchDate(2023, 3, 25, 13, 45, 1);

        serviceRegistry.add(
            "localization",
            makeFakeLocalizationService({
                dateFormat: "dd/MM/yyyy",
                timeFormat: "HH:mm:ss",
            })
        );

        isSmall = false;
        env = await makeTestEnv();
        Object.defineProperty(env, "isSmall", { get: () => isSmall });
    });

    QUnit.module("DateTimePicker");

    //-------------------------------------------------------------------------
    // Layout
    //-------------------------------------------------------------------------

    QUnit.test("default params", async (assert) => {
        const fixture = getFixture();
        await mountPicker();

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), range(24, String));
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.strictEqual(
            fixture
                .querySelector(".o_datetime_picker")
                .style.getPropertyValue("--DateTimePicker__Day-template-columns"),
            "8"
        );
    });

    QUnit.test("minDate: correct days/month/year/decades are disabled", async (assert) => {
        const fixture = getFixture();
        await mountPicker({
            minDate: DateTime.fromISO("2023-04-20T00:00:00.000"),
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
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), range(24, String));
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(12, (i) => pad2(i * 5))
        );

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "2023");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),

            ["Jan", "Feb", "Mar"],
            "correct months are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),
            ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "correct months are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "Apr");

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "2019 - 2030");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),

            ["2019", "2020", "2021", "2022"],
            "correct years are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),
            ["2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"],
            "correct years are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "2023");

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "1990 - 2100");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),
            ["1990", "2000", "2010"],
            "correct decades are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),

            ["2020", "2030", "2040", "2050", "2060", "2070", "2080", "2090", "2100"],
            "correct decades are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "2020");

        await click(fixture, ".o_today");
        await click(fixture, ".o_today");
        await click(fixture, ".o_today");

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
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });
    });

    QUnit.test("maxDate: correct days/month/year/decades are disabled", async (assert) => {
        const fixture = getFixture();
        await mountPicker({
            maxDate: DateTime.fromISO("2023-04-28T00:00:00.000"),
        });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, -29],
                        [-30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), range(24, String));
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(12, (i) => pad2(i * 5))
        );

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "2023");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),
            ["May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "correct months are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),
            ["Jan", "Feb", "Mar", "Apr"],
            "correct months are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "Apr");

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "2019 - 2030");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),

            ["2024", "2025", "2026", "2027", "2028", "2029", "2030"],
            "correct years are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),
            ["2019", "2020", "2021", "2022", "2023"],
            "correct years are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "2023");

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "1990 - 2100");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),
            ["2030", "2040", "2050", "2060", "2070", "2080", "2090", "2100"],
            "correct decades are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),

            ["1990", "2000", "2010", "2020"],
            "correct decades are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "2020");

        await click(fixture, ".o_today");
        await click(fixture, ".o_today");
        await click(fixture, ".o_today");

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, -29],
                        [-30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });
    });

    QUnit.test("min+max date: correct days/month/year/decades are disabled", async (assert) => {
        const fixture = getFixture();
        await mountPicker({
            minDate: DateTime.fromISO("2023-04-20T00:00:00.000"),
            maxDate: DateTime.fromISO("2023-04-28T00:00:00.000"),
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
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), range(24, String));
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(12, (i) => pad2(i * 5))
        );

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "2023");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),
            ["Jan", "Feb", "Mar", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "correct months are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),
            ["Apr"],
            "correct months are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "Apr");

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "2019 - 2030");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),
            [
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
            ],
            "correct years are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),
            ["2023"],
            "correct years are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "2023");

        await click(fixture, ".o_zoom_out");
        assert.equal(fixture.querySelector(".o_datetime_picker_header").textContent, "1990 - 2100");
        assert.deepEqual(
            getTexts(".o_date_item_cell[disabled]"),
            [
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
            ],
            "correct decades are disabled"
        );
        assert.deepEqual(
            getTexts(".o_date_item_cell:not([disabled])"),

            ["2020"],
            "correct decades are enabled"
        );
        assert.equal($(fixture).find(".o_date_item_cell.o_today").text(), "2020");

        await click(fixture, ".o_today");
        await click(fixture, ".o_today");
        await click(fixture, ".o_today");

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
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[13, 0]],
        });
    });

    QUnit.test("twelve-hour clock with non-null focus date index", async (assert) => {
        // Test the case when we have focusDateIndex != 0
        useTwelveHourClockFormat();
        await mountPicker({
            onSelect: (value) => {
                assert.step(formatForStep(value));
            },
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 11, minute: 16 }),
            ],
            focusedDateIndex: 1,
        });
        const [hourSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "7");
        assert.verifySteps(["2023-04-20T08:43:00,2023-04-23T07:16:00"]);
    });

    QUnit.test("twelve-hour clock", async (assert) => {
        useTwelveHourClockFormat();

        await mountPicker();

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
            time: [[1, 0, "PM"]],
        });

        const [hourSelect, minuteSelect, meridiemSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), ["12", ...range(12, String).slice(1)]);
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.deepEqual(getTexts(meridiemSelect, "option"), ["AM", "PM"]);
    });

    QUnit.test("hide time picker", async (assert) => {
        await mountPicker({
            type: "date",
        });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
        });
    });

    QUnit.test("focus is adjusted to selected date", async (assert) => {
        await mountPicker({
            value: DateTime.fromObject({ month: 5, day: 29, hour: 23, minute: 55 }),
        });

        assertDateTimePicker({
            title: "May 2023",
            date: [
                {
                    cells: [
                        [-30, 1, 2, 3, 4, 5, 6],
                        [7, 8, 9, 10, 11, 12, 13],
                        [14, 15, 16, 17, 18, 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, [29], 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [18, 19, 20, 21, 22, 23],
                },
            ],
            time: [[23, 55]],
        });
    });

    QUnit.test("next month and previous month", async (assert) => {
        await mountPicker({
            type: "date",
        });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
        });

        await click(getFixture(), ".o_previous");

        assertDateTimePicker({
            title: "March 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, 1, 2, 3, 4],
                        [5, 6, 7, 8, 9, 10, 11],
                        [12, 13, 14, 15, 16, 17, 18],
                        [19, 20, 21, 22, 23, 24, 25],
                        [26, 27, 28, 29, 30, 31, -1],
                        [-2, -3, -4, -5, -6, -7, -8],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [9, 10, 11, 12, 13, 14],
                },
            ],
        });

        await click(getFixture(), ".o_next");

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [13, 14, 15, 16, 17, 18],
                },
            ],
        });

        await click(getFixture(), ".o_next");

        assertDateTimePicker({
            title: "May 2023",
            date: [
                {
                    cells: [
                        [-30, 1, 2, 3, 4, 5, 6],
                        [7, 8, 9, 10, 11, 12, 13],
                        [14, 15, 16, 17, 18, 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, 29, 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [18, 19, 20, 21, 22, 23],
                },
            ],
        });
    });

    QUnit.test("additional month, hide time picker", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ hour: 9, minute: 36 }),
                DateTime.fromObject({ hour: 21, minute: 5 }),
            ],
            range: true,
            type: "date",
        });

        assertDateTimePicker({
            title: ["April 2023", "May 2023"],
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, ["25"], 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
                {
                    cells: [
                        [-30, 1, 2, 3, 4, 5, 6],
                        [7, 8, 9, 10, 11, 12, 13],
                        [14, 15, 16, 17, 18, 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, 29, 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
        });
    });

    QUnit.test("additional month, empty range value", async (assert) => {
        const fixture = getFixture();
        await mountPicker({
            value: [null, null],
            range: true,
        });

        assertDateTimePicker({
            title: ["April 2023", "May 2023"],
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
                {
                    cells: [
                        [-30, 1, 2, 3, 4, 5, 6],
                        [7, 8, 9, 10, 11, 12, 13],
                        [14, 15, 16, 17, 18, 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, 29, 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [
                [13, 0],
                [13, 0],
            ],
        });

        const [firstTimePicker, secondTimePicker] = getTimePickers();
        assert.deepEqual(getTexts(firstTimePicker[0], "option"), range(24, String));
        assert.deepEqual(
            getTexts(firstTimePicker[1], "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.deepEqual(getTexts(secondTimePicker[0], "option"), range(24, String));
        assert.deepEqual(
            getTexts(secondTimePicker[1], "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.strictEqual(
            fixture
                .querySelector(".o_datetime_picker")
                .style.getPropertyValue("--DateTimePicker__Day-template-columns"),
            "7"
        );
    });

    QUnit.test("range value", async (assert) => {
        const fixture = getFixture();
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 5, hour: 17, minute: 18 }),
                DateTime.fromObject({ month: 5, day: 18, hour: 5, minute: 25 }),
            ],
            range: true,
        });

        assertDateTimePicker({
            title: ["April 2023", "May 2023"],
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, [5], [6], [7], [8]],
                        [[9], [10], [11], [12], [13], [14], [15]],
                        [[16], [17], [18], [19], [20], [21], [22]],
                        [[23], [24], ["25"], [26], [27], [28], [29]],
                        [[30], -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
                {
                    cells: [
                        [-30, [1], [2], [3], [4], [5], [6]],
                        [[7], [8], [9], [10], [11], [12], [13]],
                        [[14], [15], [16], [17], [18], 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, 29, 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [
                [17, 0],
                [5, 25],
            ],
        });

        const [firstTimePicker, secondTimePicker] = getTimePickers();
        assert.deepEqual(getTexts(firstTimePicker[0], "option"), range(24, String));
        assert.deepEqual(
            getTexts(firstTimePicker[1], "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.deepEqual(getTexts(secondTimePicker[0], "option"), range(24, String));
        assert.deepEqual(
            getTexts(secondTimePicker[1], "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.strictEqual(
            fixture
                .querySelector(".o_datetime_picker")
                .style.getPropertyValue("--DateTimePicker__Day-template-columns"),
            "7"
        );
    });

    QUnit.test("range value on small device", async (assert) => {
        const fixture = getFixture();
        isSmall = true;

        await mountPicker({
            value: [
                DateTime.fromObject({ hour: 9, minute: 36 }),
                DateTime.fromObject({ hour: 21, minute: 5 }),
            ],
            range: true,
        });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, ["25"], 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [
                [9, 0],
                [21, 5],
            ],
        });

        const [firstTimePicker, secondTimePicker] = getTimePickers();
        assert.deepEqual(getTexts(firstTimePicker[0], "option"), range(24, String));
        assert.deepEqual(
            getTexts(firstTimePicker[1], "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.deepEqual(getTexts(secondTimePicker[0], "option"), range(24, String));
        assert.deepEqual(
            getTexts(secondTimePicker[1], "option"),
            range(12, (i) => pad2(i * 5))
        );
        assert.strictEqual(
            fixture
                .querySelector(".o_datetime_picker")
                .style.getPropertyValue("--DateTimePicker__Day-template-columns"),
            "7"
        );
    });

    QUnit.test("range value, previous month", async (assert) => {
        await mountPicker({
            value: [false, false],
            range: true,
        });

        assertDateTimePicker({
            title: ["April 2023", "May 2023"],
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
                {
                    cells: [
                        [-30, 1, 2, 3, 4, 5, 6],
                        [7, 8, 9, 10, 11, 12, 13],
                        [14, 15, 16, 17, 18, 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, 29, 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [
                [13, 0],
                [13, 0],
            ],
        });

        await click(getFixture(), ".o_previous");

        assertDateTimePicker({
            title: ["March 2023", "April 2023"],
            date: [
                {
                    cells: [
                        [-26, -27, -28, 1, 2, 3, 4],
                        [5, 6, 7, 8, 9, 10, 11],
                        [12, 13, 14, 15, 16, 17, 18],
                        [19, 20, 21, 22, 23, 24, 25],
                        [26, 27, 28, 29, 30, 31, -1],
                        [-2, -3, -4, -5, -6, -7, -8],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [
                [13, 0],
                [13, 0],
            ],
        });
    });

    QUnit.test("days of week narrow format", async (assert) => {
        await mountPicker({ daysOfWeekFormat: "narrow" });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
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

    QUnit.test("different rounding", async (assert) => {
        await mountPicker({
            rounding: 10,
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), range(24, String));
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(6, (i) => pad2(i * 10))
        );
    });

    QUnit.test("rounding=0 enables seconds picker", async (assert) => {
        await mountPicker({
            rounding: 0,
        });

        const [hourSelect, minuteSelect, secondsSelect] = getTimePickers().at(0);
        assert.deepEqual(getTexts(hourSelect, "option"), range(24, String));
        assert.deepEqual(
            getTexts(minuteSelect, "option"),
            range(60, (i) => pad2(i))
        );
        assert.deepEqual(
            getTexts(secondsSelect, "option"),
            range(60, (i) => pad2(i))
        );
    });

    QUnit.test("no value, select date without handler", async (assert) => {
        await mountPicker();

        await click(getPickerCell("12"));

        assert.verifySteps([]); // This test just asserts that nothing happens
    });

    QUnit.test("no value, select date", async (assert) => {
        await mountPicker({
            onSelect: (value) => assert.step(formatForStep(value)),
        });

        await click(getPickerCell("5").at(0));
        await click(getPickerCell("12"));

        assert.verifySteps(["2023-04-05T13:00:00", "2023-04-12T13:00:00"]);
    });

    QUnit.test("no value, select time", async (assert) => {
        await mountPicker({
            onSelect: (value) => assert.step(formatForStep(value)),
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "18");
        await editSelect(minuteSelect, null, "5");

        assert.verifySteps(["2023-04-25T18:00:00", "2023-04-25T18:05:00"]);
    });

    QUnit.test("minDate with time: selecting out-of-range and in-range times", async (assert) => {
        await mountPicker({
            onSelect: (value) => assert.step(formatForStep(value)),
            minDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
        });

        const [hourSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "15");
        assert.verifySteps([]);
        await editSelect(hourSelect, null, "16");
        assert.verifySteps(["2023-04-25T16:00:00"]);
    });

    QUnit.test("maxDate with time: selecting out-of-range and in-range times", async (assert) => {
        await mountPicker({
            onSelect: (value) => assert.step(formatForStep(value)),
            maxDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
        });

        const [hourSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "17");
        assert.verifySteps([]);
        await editSelect(hourSelect, null, "16");
        assert.verifySteps(["2023-04-25T16:00:00"]);
    });

    QUnit.test(
        "max and min date with time: selecting out-of-range and in-range times",
        async (assert) => {
            await mountPicker({
                onSelect: (value) => assert.step(formatForStep(value)),
                minDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
                maxDate: DateTime.fromISO("2023-04-25T16:00:00.000"),
            });

            const [hourSelect] = getTimePickers().at(0);
            await editSelect(hourSelect, null, "15");
            await editSelect(hourSelect, null, "17");
            assert.verifySteps([]);
            await editSelect(hourSelect, null, "16");
            assert.verifySteps(["2023-04-25T16:00:00"]);
        }
    );

    QUnit.test(
        "max and min date with time: selecting invalid minutes and making it valid by selecting hours",
        async (assert) => {
            await mountPicker({
                onSelect: (value) => assert.step(formatForStep(value)),
                minDate: DateTime.fromISO("2023-04-25T16:10:00.000"),
                maxDate: DateTime.fromISO("2023-04-25T16:50:00.000"),
            });

            const [hourSelect, minuteSelect] = getTimePickers().at(0);
            await editSelect(hourSelect, null, "13");
            await editSelect(minuteSelect, null, "30");
            assert.verifySteps([]);
            await editSelect(hourSelect, null, "16");
            assert.verifySteps(["2023-04-25T16:30:00"]);
        }
    );

    QUnit.test(
        "max and min date with time: valid time on invalid day becomes valid when selecting day",
        async (assert) => {
            await mountPicker({
                onSelect: (value) => assert.step(formatForStep(value)),
                minDate: DateTime.fromISO("2023-04-24T16:10:00.000"),
                maxDate: DateTime.fromISO("2023-04-24T16:50:00.000"),
            });

            const [hourSelect, minuteSelect] = getTimePickers().at(0);
            await editSelect(hourSelect, null, "16");
            await editSelect(minuteSelect, null, "30");
            assert.verifySteps([]);
            await click(getPickerCell("24"));
            assert.verifySteps(["2023-04-24T16:30:00"]);
        }
    );

    QUnit.test("custom invalidity function", async (assert) => {
        await mountPicker({
            type: "date",
            // make weekends invalid
            isDateValid: (date) => date.weekday <= 5,
        });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, -1],
                        [-2, 3, 4, 5, 6, 7, -8],
                        [-9, 10, 11, 12, 13, 14, -15],
                        [-16, 17, 18, 19, 20, 21, -22],
                        [-23, 24, "25", 26, 27, 28, -29],
                        [-30, -1, -2, -3, -4, -5, -6],
                    ],
                },
            ],
        });
    });

    QUnit.test("custom date cell class function", async (assert) => {
        await mountPicker({
            type: "date",
            // give special class to weekends
            dayCellClass: (date) => (date.weekday >= 6 ? "o_weekend" : ""),
        });

        assert.deepEqual(getTexts(".o_weekend"), [
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

    QUnit.test("single value, select date", async (assert) => {
        await mountPicker({
            value: DateTime.fromObject({ day: 30, hour: 8, minute: 43 }),
            onSelect: (value) => assert.step(formatForStep(value)),
        });

        await click(getPickerCell("5").at(0));

        assert.verifySteps(["2023-04-05T08:43:00"]);
    });

    QUnit.test("single value, select time", async (assert) => {
        await mountPicker({
            value: DateTime.fromObject({ day: 30, hour: 8, minute: 43 }),
            onSelect: (value) => assert.step(formatForStep(value)),
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "18");
        await editSelect(minuteSelect, null, "5");

        assert.verifySteps(["2023-04-30T18:43:00", "2023-04-30T18:05:00"]);
    });

    QUnit.test("single value, select time in twelve-hour clock format", async (assert) => {
        useTwelveHourClockFormat();

        await mountPicker({
            value: DateTime.fromObject({ day: 30, hour: 8, minute: 43 }),
            onSelect: (value) => assert.step(formatForStep(value)),
        });

        const [hourSelect, minuteSelect, meridiemSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "7");
        await editSelect(minuteSelect, null, "5");
        await editSelect(meridiemSelect, null, "PM");

        assert.verifySteps(["2023-04-30T07:43:00", "2023-04-30T07:05:00", "2023-04-30T19:05:00"]);
    });

    QUnit.test("range value, select date for first value", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            // focusedDateIndex is implicitly 0
            onSelect: (values) => assert.step(formatForStep(values)),
        });

        await click(getPickerCell("5").at(0));

        assert.verifySteps(["2023-04-05T08:43:00,2023-04-23T17:16:00"]);
    });

    QUnit.test("range value, select time for first value", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 0,
            onSelect: (values) => assert.step(formatForStep(values)),
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "18");
        await editSelect(minuteSelect, null, "5");

        assert.verifySteps([
            "2023-04-20T18:43:00,2023-04-23T17:16:00",
            "2023-04-20T18:05:00,2023-04-23T17:16:00",
        ]);
    });

    QUnit.test("range value, select date for second value", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 1,
            onSelect: (values) => assert.step(formatForStep(values)),
        });

        await click(getPickerCell("21").at(0));

        assert.verifySteps(["2023-04-20T08:43:00,2023-04-21T17:16:00"]);
    });

    QUnit.test("range value, select time for second value", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 1,
            onSelect: (values) => assert.step(formatForStep(values)),
        });

        const [hourSelect, minuteSelect] = getTimePickers().at(1);
        await editSelect(hourSelect, null, "18");
        await editSelect(minuteSelect, null, "5");

        assert.verifySteps([
            "2023-04-20T08:43:00,2023-04-23T18:16:00",
            "2023-04-20T08:43:00,2023-04-23T18:05:00",
        ]);
    });

    QUnit.test("range value, select date for second value before first value", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 1,
            onSelect: (values) => assert.step(formatForStep(values)),
        });

        await click(getPickerCell("19").at(0));

        assert.verifySteps(["2023-04-19T08:43:00,2023-04-23T17:16:00"]);
    });

    QUnit.test("range value, select date for first value after second value", async (assert) => {
        await mountPicker({
            value: [
                DateTime.fromObject({ day: 20, hour: 8, minute: 43 }),
                DateTime.fromObject({ day: 23, hour: 17, minute: 16 }),
            ],
            range: true,
            focusedDateIndex: 0,
            onSelect: (values) => assert.step(formatForStep(values)),
        });

        await click(getPickerCell("27").at(1));

        assert.verifySteps(["2023-04-20T08:43:00,2023-04-27T17:16:00"]);
    });

    QUnit.test("focus proper month when changing props out of current month", async (assert) => {
        class Parent extends Component {
            static template = xml`<DateTimePicker value="state.current"/>`;
            static components = { DateTimePicker };
            setup() {
                this.state = useState({
                    current: DateTime.now(),
                });
            }
        }

        const parent = await mount(Parent, getFixture(), { env });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, ["25"], 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [[13, 45]],
        });

        parent.state.current = DateTime.fromObject({ month: 5, day: 1, hour: 17, minute: 16 });
        await nextTick();

        assertDateTimePicker({
            title: "May 2023",
            date: [
                {
                    cells: [
                        [-30, [1], 2, 3, 4, 5, 6],
                        [7, 8, 9, 10, 11, 12, 13],
                        [14, 15, 16, 17, 18, 19, 20],
                        [21, 22, 23, 24, 25, 26, 27],
                        [28, 29, 30, 31, -1, -2, -3],
                        [-4, -5, -6, -7, -8, -9, -10],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                },
            ],
            time: [[17, 0]],
        });
    });

    QUnit.test("disable show week numbers", async (assert) => {
        const fixture = getFixture();
        await mountPicker({ showWeekNumbers: false });

        assertDateTimePicker({
            title: "April 2023",
            date: [
                {
                    cells: [
                        [-26, -27, -28, -29, -30, -31, 1],
                        [2, 3, 4, 5, 6, 7, 8],
                        [9, 10, 11, 12, 13, 14, 15],
                        [16, 17, 18, 19, 20, 21, 22],
                        [23, 24, "25", 26, 27, 28, 29],
                        [30, -1, -2, -3, -4, -5, -6],
                    ],
                    daysOfWeek: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [],
                },
            ],
            time: [[13, 0]],
        });
        assert.strictEqual(
            fixture
                .querySelector(".o_datetime_picker")
                .style.getPropertyValue("--DateTimePicker__Day-template-columns"),
            "7"
        );
    });
});
