import { describe, expect, test } from "@odoo/hoot";
import { FAKE_FIELDS } from "./calendar_test_helpers";

import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser";

describe.current.tags("headless");

const parser = new CalendarArchParser();
const DEFAULT_ARCH_RESULTS = {
    canCreate: true,
    canDelete: true,
    canEdit: true,
    eventLimit: 5,
    fieldMapping: {
        date_start: "start_date",
    },
    fieldNames: ["start_date"],
    filtersInfo: {},
    formViewId: false,
    hasEditDialog: false,
    quickCreate: true,
    quickCreateViewId: null,
    isDateHidden: false,
    isTimeHidden: false,
    popoverFieldNodes: {},
    scale: "week",
    scales: ["day", "week", "month", "year"],
    showUnusualDays: false,
};

function parseArch(arch) {
    return parser.parse(arch, { fake: { fields: FAKE_FIELDS } }, "fake");
}

function parseWith(attrs) {
    const str = Object.entries(attrs)
        .map(([k, v]) => `${k}="${v}"`)
        .join(" ");
    return parseArch(`<calendar date_start="start_date" ${str}/>`);
}

test(`throw if date_start is not set`, () => {
    expect(() => parseArch(`<calendar/>`)).toThrow(
        `Calendar view has not defined "date_start" attribute.`
    );
});

test(`defaults`, () => {
    expect(parseArch(`<calendar date_start="start_date"/>`)).toEqual(DEFAULT_ARCH_RESULTS);
});

test("canCreate", () => {
    expect(parseWith({ create: "" }).canCreate).toBe(true);

    expect(parseWith({ create: "true" }).canCreate).toBe(true);
    expect(parseWith({ create: "True" }).canCreate).toBe(true);
    expect(parseWith({ create: "1" }).canCreate).toBe(true);

    expect(parseWith({ create: "false" }).canCreate).toBe(false);
    expect(parseWith({ create: "False" }).canCreate).toBe(false);
    expect(parseWith({ create: "0" }).canCreate).toBe(false);
});

test("canDelete", () => {
    expect(parseWith({ delete: "" }).canDelete).toBe(true);

    expect(parseWith({ delete: "true" }).canDelete).toBe(true);
    expect(parseWith({ delete: "True" }).canDelete).toBe(true);
    expect(parseWith({ delete: "1" }).canDelete).toBe(true);

    expect(parseWith({ delete: "false" }).canDelete).toBe(false);
    expect(parseWith({ delete: "False" }).canDelete).toBe(false);
    expect(parseWith({ delete: "0" }).canDelete).toBe(false);
});

test("canEdit", () => {
    expect(parseWith({ edit: "" }).canEdit).toBe(true);

    expect(parseWith({ edit: "true" }).canEdit).toBe(true);
    expect(parseWith({ edit: "True" }).canEdit).toBe(true);
    expect(parseWith({ edit: "1" }).canEdit).toBe(true);

    expect(parseWith({ edit: "false" }).canEdit).toBe(false);
    expect(parseWith({ edit: "False" }).canEdit).toBe(false);
    expect(parseWith({ edit: "0" }).canEdit).toBe(false);
});

test("eventLimit", () => {
    expect(parseWith({ event_limit: "2" }).eventLimit).toBe(2);
    expect(parseWith({ event_limit: "5" }).eventLimit).toBe(5);

    expect(() => parseWith({ event_limit: "five" })).toThrow();
    expect(() => parseWith({ event_limit: "" })).toThrow();
});

test("hasEditDialog", () => {
    expect(parseWith({ event_open_popup: "" }).hasEditDialog).toBe(false);

    expect(parseWith({ event_open_popup: "true" }).hasEditDialog).toBe(true);
    expect(parseWith({ event_open_popup: "True" }).hasEditDialog).toBe(true);
    expect(parseWith({ event_open_popup: "1" }).hasEditDialog).toBe(true);

    expect(parseWith({ event_open_popup: "false" }).hasEditDialog).toBe(false);
    expect(parseWith({ event_open_popup: "False" }).hasEditDialog).toBe(false);
    expect(parseWith({ event_open_popup: "0" }).hasEditDialog).toBe(false);
});

test("quickCreate", () => {
    expect(parseWith({ quick_create: "" }).quickCreate).toBe(true);

    expect(parseWith({ quick_create: "true" }).quickCreate).toBe(true);
    expect(parseWith({ quick_create: "True" }).quickCreate).toBe(true);
    expect(parseWith({ quick_create: "1" }).quickCreate).toBe(true);

    expect(parseWith({ quick_create: "false" }).quickCreate).toBe(false);
    expect(parseWith({ quick_create: "False" }).quickCreate).toBe(false);
    expect(parseWith({ quick_create: "0" }).quickCreate).toBe(false);

    expect(parseWith({ quick_create: "12" }).quickCreate).toBe(true);
});

test("quickCreateViewId", () => {
    expect(parseWith({ quick_create: "0", quick_create_view_id: "12" })).toEqual({
        ...DEFAULT_ARCH_RESULTS,
        quickCreate: false,
        quickCreateViewId: null,
    });
    expect(parseWith({ quick_create: "1", quick_create_view_id: "12" })).toEqual({
        ...DEFAULT_ARCH_RESULTS,
        quickCreate: true,
        quickCreateViewId: 12,
    });
    expect(parseWith({ quick_create: "1" })).toEqual({
        ...DEFAULT_ARCH_RESULTS,
        quickCreate: true,
        quickCreateViewId: null,
    });
});

test("isDateHidden", () => {
    expect(parseWith({ hide_date: "" }).isDateHidden).toBe(false);

    expect(parseWith({ hide_date: "true" }).isDateHidden).toBe(true);
    expect(parseWith({ hide_date: "True" }).isDateHidden).toBe(true);
    expect(parseWith({ hide_date: "1" }).isDateHidden).toBe(true);

    expect(parseWith({ hide_date: "false" }).isDateHidden).toBe(false);
    expect(parseWith({ hide_date: "False" }).isDateHidden).toBe(false);
    expect(parseWith({ hide_date: "0" }).isDateHidden).toBe(false);
});

test("isTimeHidden", () => {
    expect(parseWith({ hide_time: "" }).isTimeHidden).toBe(false);

    expect(parseWith({ hide_time: "true" }).isTimeHidden).toBe(true);
    expect(parseWith({ hide_time: "True" }).isTimeHidden).toBe(true);
    expect(parseWith({ hide_time: "1" }).isTimeHidden).toBe(true);

    expect(parseWith({ hide_time: "false" }).isTimeHidden).toBe(false);
    expect(parseWith({ hide_time: "False" }).isTimeHidden).toBe(false);
    expect(parseWith({ hide_time: "0" }).isTimeHidden).toBe(false);
});

test("scale", () => {
    expect(parseWith({ mode: "day" }).scale).toBe("day");
    expect(parseWith({ mode: "week" }).scale).toBe("week");
    expect(parseWith({ mode: "month" }).scale).toBe("month");
    expect(parseWith({ mode: "year" }).scale).toBe("year");

    expect(() => parseWith({ mode: "" })).toThrow(`Calendar view cannot display mode: `);
    expect(() => parseWith({ mode: "other" })).toThrow(`Calendar view cannot display mode: other`);
});

test("scales", () => {
    expect(parseWith({ scales: "" }).scales).toEqual([]);

    expect(parseWith({ scales: "day" }).scales).toEqual(["day"]);
    expect(parseWith({ scales: "day,week" }).scales).toEqual(["day", "week"]);
    expect(parseWith({ scales: "day,week,month" }).scales).toEqual(["day", "week", "month"]);
    expect(parseWith({ scales: "day,week,month,year" }).scales).toEqual([
        "day",
        "week",
        "month",
        "year",
    ]);
    expect(parseWith({ scales: "week" }).scales).toEqual(["week"]);
    expect(parseWith({ scales: "week,month" }).scales).toEqual(["week", "month"]);
    expect(parseWith({ scales: "week,month,year" }).scales).toEqual(["week", "month", "year"]);
    expect(parseWith({ scales: "month" }).scales).toEqual(["month"]);
    expect(parseWith({ scales: "month,year" }).scales).toEqual(["month", "year"]);
    expect(parseWith({ scales: "year" }).scales).toEqual(["year"]);
    expect(parseWith({ scales: "year,day,month,week" }).scales).toEqual([
        "year",
        "day",
        "month",
        "week",
    ]);

    expect(() =>
        parseArch(`<calendar date_start="start_date" scales="month" mode="day"/>`)
    ).toThrow();
});

test("showUnusualDays", () => {
    expect(parseWith({ show_unusual_days: "" }).showUnusualDays).toBe(false);

    expect(parseWith({ show_unusual_days: "true" }).showUnusualDays).toBe(true);
    expect(parseWith({ show_unusual_days: "True" }).showUnusualDays).toBe(true);
    expect(parseWith({ show_unusual_days: "1" }).showUnusualDays).toBe(true);

    expect(parseWith({ show_unusual_days: "false" }).showUnusualDays).toBe(false);
    expect(parseWith({ show_unusual_days: "False" }).showUnusualDays).toBe(false);
    expect(parseWith({ show_unusual_days: "0" }).showUnusualDays).toBe(false);
});
