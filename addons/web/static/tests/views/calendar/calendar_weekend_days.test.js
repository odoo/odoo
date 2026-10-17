import { beforeEach, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    preloadBundle,
} from "@web/../tests/web_test_helpers";
import { changeScale } from "./calendar_test_helpers";

class CalendarEvent extends models.Model {
    _name = "calendar.event";
    name = fields.Char();
    start = fields.Date();
    stop = fields.Date();
}

defineModels([CalendarEvent]);
preloadBundle("web.fullcalendar_lib");

beforeEach(() => {
    mockDate("2021-07-16");
});

async function start(scale, weekendDays) {
    if (weekendDays !== undefined) {
        patchWithCleanup(user, {
            get activeCompany() {
                return { id: 1, calendar_weekend_days: weekendDays };
            },
        });
    }
    browser.localStorage.setItem("calendar.isWeekendVisible", "false");
    return mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar date_start="start" date_stop="stop" mode="${scale}"><field name="name"/></calendar>`,
    });
}

function expectVisible(date, visible) {
    const selector = `.o_calendar_widget [data-date="${date}"]`;
    if (visible) {
        expect(selector).not.toHaveCount(0);
    } else {
        expect(selector).toHaveCount(0);
    }
}

for (const scale of ["week", "month", "year"]) {
    for (const weekendDays of [[5], [5, 6], [0, 6], []]) {
        test(`${scale}: hide company weekend days ${JSON.stringify(weekendDays)}`, async () => {
            await start(scale, weekendDays);
            expectVisible("2021-07-16", !weekendDays.includes(5));
            expectVisible("2021-07-17", !weekendDays.includes(6));
            expectVisible("2021-07-11", !weekendDays.includes(0));

            await contains(".scale_button_selection").click();
            await contains(".o_show_weekends").click();
            expectVisible("2021-07-16", true);
            expectVisible("2021-07-17", true);
            expectVisible("2021-07-11", true);
        });
    }
}

test("default weekend days when company information is unavailable", async () => {
    patchWithCleanup(user, {
        get activeCompany() {
            return undefined;
        },
    });
    await start("week");
    expectVisible("2021-07-16", true);
    expectVisible("2021-07-17", false);
    expectVisible("2021-07-11", false);
});

test("a hidden Friday remains visible in day scale", async () => {
    await start("week", [5]);
    expectVisible("2021-07-16", false);
    await changeScale("day");
    expectVisible("2021-07-16", true);
    await changeScale("month");
    expectVisible("2021-07-16", false);
});
