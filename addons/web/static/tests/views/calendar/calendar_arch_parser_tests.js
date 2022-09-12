/** @odoo-module **/

import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser";
import { FAKE_DATE, FAKE_FIELDS, makeEnv } from "./calendar_helpers";

function parseArch(arch, options = {}) {
    const parser = new CalendarArchParser();
    return parser.parse(
        arch,
        { fake: "fields" in options ? options.fields : FAKE_FIELDS },
        "fake",
        options.context || {},
        "date" in options ? options.date : FAKE_DATE
    );
}

function check(assert, paramName, paramValue, expectedName, expectedValue) {
    const arch = `<calendar date_start="start_date" ${paramName}="${paramValue}" />`;
    const data = parseArch(arch);
    assert.strictEqual(data[expectedName], expectedValue);
}

QUnit.module("CalendarArchParser");

QUnit.test("throw if date_start is not set", (assert) => {
    assert.throws(() => {
        parseArch(`<calendar />`);
    });
});

QUnit.test("defaults", (assert) => {
    assert.deepEqual(parseArch(`<calendar date_start="start_date" />`), {
        canCreate: true,
        canDelete: true,
        canEdit: true,
        // date: FAKE_DATE,
        eventLimit: 5,
        fieldMapping: {
            date_start: "start_date",
        },
        fieldNames: ["start_date"],
        filtersInfo: {},
        formViewId: false,
        hasEditDialog: false,
        hasQuickCreate: true,
        isDateHidden: false,
        isTimeHidden: false,
        popoverFields: {},
        scale: "week",
        scales: ["day", "week", "month", "year"],
        showUnusualDays: false,
    });
});

QUnit.test("canCreate", (assert) => {
    check(assert, "create", "", "canCreate", true);
    check(assert, "create", "true", "canCreate", true);
    check(assert, "create", "True", "canCreate", true);
    check(assert, "create", "1", "canCreate", true);
    check(assert, "create", "false", "canCreate", false);
    check(assert, "create", "False", "canCreate", false);
    check(assert, "create", "0", "canCreate", false);
});

QUnit.test("canDelete", (assert) => {
    check(assert, "delete", "", "canDelete", true);
    check(assert, "delete", "true", "canDelete", true);
    check(assert, "delete", "True", "canDelete", true);
    check(assert, "delete", "1", "canDelete", true);
    check(assert, "delete", "false", "canDelete", false);
    check(assert, "delete", "False", "canDelete", false);
    check(assert, "delete", "0", "canDelete", false);
});

QUnit.test("canEdit", (assert) => {
    const fields = { ...FAKE_FIELDS };

    fields.start_date.readonly = false;
    assert.strictEqual(parseArch(`<calendar date_start="start_date" />`, { fields }).canEdit, true);

    fields.start_date.readonly = true;
    assert.strictEqual(
        parseArch(`<calendar date_start="start_date" />`, { fields }).canEdit,
        false
    );
});

QUnit.skipWOWL("date", async (assert) => {
    let date = parseArch(`<calendar date_start="start_date" />`, { date: FAKE_DATE }).date;
    assert.ok(date.equals(FAKE_DATE));

    await makeEnv(); // we need localization service
    date = parseArch(`<calendar date_start="start_date" />`, {
        context: { initial_date: "2021-07-16 08:00:00" },
    }).date;
    assert.ok(date.equals(luxon.DateTime.utc(2021, 7, 16, 8, 0, 0)));

    date = parseArch(`<calendar date_start="start_date" />`, {
        date: null, // force default date
    }).date;
    assert.ok(date.diff(luxon.DateTime.utc(), "seconds").seconds < 1);
});

QUnit.test("eventLimit", (assert) => {
    check(assert, "event_limit", "2", "eventLimit", 2);
    check(assert, "event_limit", "5", "eventLimit", 5);

    assert.throws(() => {
        parseArch(`<calendar date_start="start_date" event_limit="five" />`);
    });

    assert.throws(() => {
        parseArch(`<calendar date_start="start_date" event_limit="" />`);
    });
});

QUnit.skipWOWL("formViewId", (assert) => {
    check(assert, "form_view_id", "", "formViewId", null);
    check(assert, "form_view_id", "153", "formViewId", 153);

    assert.throws(() => {
        parseArch(`<calendar date_start="start_date" form_view_id="one" />`);
    });
});

QUnit.test("hasEditDialog", (assert) => {
    check(assert, "event_open_popup", "", "hasEditDialog", false);
    check(assert, "event_open_popup", "true", "hasEditDialog", true);
    check(assert, "event_open_popup", "True", "hasEditDialog", true);
    check(assert, "event_open_popup", "1", "hasEditDialog", true);
    check(assert, "event_open_popup", "false", "hasEditDialog", false);
    check(assert, "event_open_popup", "False", "hasEditDialog", false);
    check(assert, "event_open_popup", "0", "hasEditDialog", false);
});

QUnit.test("hasQuickCreate", (assert) => {
    check(assert, "quick_add", "", "hasQuickCreate", true);
    check(assert, "quick_add", "true", "hasQuickCreate", true);
    check(assert, "quick_add", "True", "hasQuickCreate", true);
    check(assert, "quick_add", "1", "hasQuickCreate", true);
    check(assert, "quick_add", "false", "hasQuickCreate", false);
    check(assert, "quick_add", "False", "hasQuickCreate", false);
    check(assert, "quick_add", "0", "hasQuickCreate", false);
});

QUnit.test("isDateHidden", (assert) => {
    check(assert, "hide_date", "", "isDateHidden", false);
    check(assert, "hide_date", "true", "isDateHidden", true);
    check(assert, "hide_date", "True", "isDateHidden", true);
    check(assert, "hide_date", "1", "isDateHidden", true);
    check(assert, "hide_date", "false", "isDateHidden", false);
    check(assert, "hide_date", "False", "isDateHidden", false);
    check(assert, "hide_date", "0", "isDateHidden", false);
});

QUnit.test("isTimeHidden", (assert) => {
    check(assert, "hide_time", "", "isTimeHidden", false);
    check(assert, "hide_time", "true", "isTimeHidden", true);
    check(assert, "hide_time", "True", "isTimeHidden", true);
    check(assert, "hide_time", "1", "isTimeHidden", true);
    check(assert, "hide_time", "false", "isTimeHidden", false);
    check(assert, "hide_time", "False", "isTimeHidden", false);
    check(assert, "hide_time", "0", "isTimeHidden", false);
});

QUnit.test("scale", (assert) => {
    check(assert, "mode", "day", "scale", "day");
    check(assert, "mode", "week", "scale", "week");
    check(assert, "mode", "month", "scale", "month");
    check(assert, "mode", "year", "scale", "year");
    assert.throws(() => {
        parseArch(`<calendar date_start="start_date" mode="other" />`);
    });

    assert.throws(() => {
        parseArch(`<calendar date_start="start_date" mode="" />`);
    });
});

QUnit.test("scales", (assert) => {
    function check(scales, expectedScales) {
        const arch = `<calendar date_start="start_date" scales="${scales}" />`;
        const data = parseArch(arch);
        assert.deepEqual(data.scales, expectedScales);
    }

    check("", []);

    check("day", ["day"]);
    check("day,week", ["day", "week"]);
    check("day,week,month", ["day", "week", "month"]);
    check("day,week,month,year", ["day", "week", "month", "year"]);
    check("week", ["week"]);
    check("week,month", ["week", "month"]);
    check("week,month,year", ["week", "month", "year"]);
    check("month", ["month"]);
    check("month,year", ["month", "year"]);
    check("year", ["year"]);

    check("year,day,month,week", ["year", "day", "month", "week"]);

    assert.throws(() => {
        parseArch(`<calendar date_start="start_date" scales="month" mode="day" />`);
    });
});

QUnit.test("showUnusualDays", (assert) => {
    check(assert, "show_unusual_days", "", "showUnusualDays", false);
    check(assert, "show_unusual_days", "true", "showUnusualDays", true);
    check(assert, "show_unusual_days", "True", "showUnusualDays", true);
    check(assert, "show_unusual_days", "1", "showUnusualDays", true);
    check(assert, "show_unusual_days", "false", "showUnusualDays", false);
    check(assert, "show_unusual_days", "False", "showUnusualDays", false);
    check(assert, "show_unusual_days", "0", "showUnusualDays", false);
});
