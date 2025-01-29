import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAllTexts, edit, animationFrame } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { defineParams, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { TimePicker } from "@web/core/datetime/time_picker";

/**
 * @param {any} value
 */
const pad2 = (value) => String(value).padStart(2, "0");

/**
 * @template {any} [T=number]
 * @param {number} length
 * @param {(index: number) => T} mapping
 */
const range = (length, mapping = (n) => n) => [...Array(length)].map((_, i) => mapping(i));

const getTimeOptions = (rounding = 15) => {
    const _hours = range(24, String);
    const _minutes = range(60, (i) => i)
        .filter((i) => i % rounding === 0)
        .map((i) => pad2(i));
    return _hours.flatMap((h) => _minutes.map((m) => `${h}:${m}`));
};

defineParams({
    lang_parameters: {
        date_format: "%d/%m/%Y",
        time_format: "%H:%M:%S",
    },
});

beforeEach(() => mockDate("2023-04-25T12:45:01"));

test("default params, click on suggestion to select time", async () => {
    await mountWithCleanup(TimePicker);

    expect(".o_time_picker").toHaveCount(1);
    expect("input.o_time_picker_input").toHaveValue("0:00");

    await click(".o_time_picker_input");
    await animationFrame();

    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(1);
    expect(queryAllTexts(".o_time_picker_option")).toEqual(getTimeOptions());

    await click(".o_time_picker_option:contains(12:15)");
    await animationFrame();

    expect("input.o_time_picker_input").toHaveValue("12:15");
});

test("Enter triggers onChange", async () => {
    await mountWithCleanup(TimePicker);

    expect(".o_time_picker").toHaveCount(1);

    await click(".o_time_picker_input");
    await animationFrame();

    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(1);
    expect(queryAllTexts(".o_time_picker_option")).toEqual(getTimeOptions());

    await edit("12:13", { confirm: "enter" });
    await animationFrame();

    expect("input.o_time_picker_input").toHaveValue("12:15");
});
