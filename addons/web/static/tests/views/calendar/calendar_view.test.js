import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { mockTimeZone } from "@odoo/hoot-mock";

import {
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

class Event extends models.Model {
    name = fields.Char();
    start = fields.Datetime();
    stop = fields.Datetime();

    check_access_rights = function () {
        return Promise.resolve(true);
    };

    _records = [
        {
            id: 1,
            name: "May Day",
            start: "2024-05-01 08:00:00",
            stop: "2024-05-01 18:00:00",
        },
    ];
}

defineModels([Event]);

const MON_TO_SUN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

async function setupCalendarView(mode, options = {}) {
    const { utc_offset, week_start } = options;
    mockTimeZone(utc_offset ?? 0);
    defineParams({ lang_parameters: { week_start: week_start ?? 1 } });
    return await mountView({
        type: "calendar",
        resModel: "event",
        resId: 1,
        arch: /* xml */ `<calendar mode="${mode}" date_start="start"/>`,
    });
}

function weekDaysTest(mode, options) {
    return async () => {
        expect.assertions(8);
        await setupCalendarView(mode, options);

        const { week_start } = options;
        const week =
            week_start === 1
                ? MON_TO_SUN
                : MON_TO_SUN.map((_, i) => MON_TO_SUN[(week_start + i - 1) % 7]);

        expect(queryAllTexts(".o_cw_day_name")).toEqual(week);
        for (const day of week) {
            expect(`.fc-day-${day.toLowerCase()} .o_cw_day_name`).toHaveText(day);
        }
    };
}

describe("EU", () => {
    const options = { utc_offset: +2, week_start: 1 };
    test("week days (week view)", weekDaysTest("week", options));
    test("week days (month view)", weekDaysTest("month", options));
});

describe("US", () => {
    const options = { utc_offset: -7, week_start: 7 };
    test("week days (week view)", weekDaysTest("week", options));
    test("week days (month view)", weekDaysTest("month", options));
});
