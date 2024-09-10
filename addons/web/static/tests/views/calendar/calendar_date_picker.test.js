import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    defineParams,
    fields,
    findComponent,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { CalendarController } from "@web/views/calendar/calendar_controller";
import { changeScale } from "./calendar_test_helpers";

describe.current.tags("desktop");

class Event extends models.Model {
    name = fields.Char();
    start = fields.Date();

    has_access() {
        return true;
    }
}

defineModels([Event]);

beforeEach(() => {
    mockDate("2021-08-14T08:00:00");
});

test(`Mount a CalendarDatePicker`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="day"/>`,
    });
    expect(`.o_datetime_picker`).toHaveCount(1);
    expect(`.o_datetime_picker .o_selected`).toHaveCount(1);
    expect(`.o_datetime_picker .o_selected`).toHaveText("14");
    expect(`.o_datetime_picker_header .o_datetime_button`).toHaveText("August 2021");
    expect(queryAllTexts`.o_datetime_picker .o_day_of_week_cell`).toEqual([
        "S",
        "M",
        "T",
        "W",
        "T",
        "F",
        "S",
    ]);
});

test(`Scale: init with day`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="day"/>`,
    });
    expect(`.o_datetime_picker .o_highlighted`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_start`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_end`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlighted`).toHaveText("14");
});

test(`Scale: init with week`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });
    expect(`.o_datetime_picker .o_highlighted`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_start`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_end`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlighted`).toHaveText("14");
});

test(`Scale: init with month`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="month"/>`,
    });
    expect(`.o_datetime_picker .o_highlighted`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_start`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_end`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlighted`).toHaveText("14");
});

test(`Scale: init with year`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="year"/>`,
    });
    expect(`.o_datetime_picker .o_highlighted`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_start`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlight_end`).toHaveCount(1);
    expect(`.o_datetime_picker .o_highlighted`).toHaveText("14");
});

test(`First day: 0 = Sunday`, async () => {
    // the week start depends on the locale
    defineParams({
        lang_parameters: { week_start: 0 },
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="day"/>`,
    });
    expect(queryAllTexts`.o_datetime_picker .o_day_of_week_cell`).toEqual([
        "S",
        "M",
        "T",
        "W",
        "T",
        "F",
        "S",
    ]);
});

test(`First day: 1 = Monday`, async () => {
    // the week start depends on the locale
    defineParams({
        lang_parameters: { week_start: 1 },
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="day"/>`,
    });
    expect(queryAllTexts`.o_datetime_picker .o_day_of_week_cell`).toEqual([
        "M",
        "T",
        "W",
        "T",
        "F",
        "S",
        "S",
    ]);
});

test(`Click on active day should change scale : day -> month`, async () => {
    const view = await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="day"/>`,
    });
    const calendar = findComponent(view, (component) => component instanceof CalendarController);
    await contains(`.o_datetime_picker .o_selected`).click();
    expect(calendar.model.scale).toBe("month");
    expect(calendar.model.date.valueOf()).toBe(luxon.DateTime.local(2021, 8, 14).valueOf());
});

test(`Click on active day should change scale : month -> week`, async () => {
    const view = await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="month"/>`,
    });
    const calendar = findComponent(view, (component) => component instanceof CalendarController);
    await contains(`.o_datetime_picker .o_selected`).click();
    expect(calendar.model.scale).toBe("week");
    expect(calendar.model.date.valueOf()).toBe(luxon.DateTime.local(2021, 8, 14).valueOf());
});

test(`Click on active day should change scale : week -> day`, async () => {
    const view = await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });
    const calendar = findComponent(view, (component) => component instanceof CalendarController);
    await contains(`.o_datetime_picker .o_selected`).click();
    expect(calendar.model.scale).toBe("day");
    expect(calendar.model.date.valueOf()).toBe(luxon.DateTime.local(2021, 8, 14).valueOf());
});

test(`Scale: today is correctly highlighted`, async () => {
    mockDate("2021-07-04T08:00:00");
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="month"/>`,
    });
    expect(`.o_datetime_picker .o_today`).toHaveClass("o_highlighted");
    expect(`.o_datetime_picker .o_today`).toHaveText("4");
});

test(`Scale: scale default is fetched from sessionStorage`, async () => {
    patchWithCleanup(sessionStorage, {
        setItem(key, value) {
            if (key === "calendar-scale") {
                expect.step(`scale_${value}`);
            }
        },
        getItem(key) {
            if (key === "calendar-scale") {
                return "month";
            }
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start"/>`,
    });
    expect(`.scale_button_selection`).toHaveText("Month");

    await changeScale("year");
    expect(`.scale_button_selection`).toHaveText("Year");
    expect.verifySteps(["scale_year"]);
});
