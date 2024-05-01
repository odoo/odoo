import { beforeEach, expect, test, describe } from "@odoo/hoot";
import { mockDate, advanceTime } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import {
    CalendarEvent,
    EventType,
    ResUsers,
    ResPartner,
    CalendarFilters
} from "@calendar/../tests/mock_server/mock_models/calendar_model";

defineModels([CalendarEvent, EventType, ResUsers, ResPartner, CalendarFilters]);

describe.current.tags("desktop");

beforeEach(() => {
    mockDate("2016-12-12T08:00:00", 1);
});

const calendarFilterParams = {
    resModel: "calendar.event",
    type: "calendar",
    arch: `
            <calendar js_class="attendee_calendar" date_start="start" date_stop="stop">
                <field name="partner_ids" write_model="calendar.filters" write_field="partner_id"/>
            </calendar>
        `,
}

onRpc(async ({ args, method, model }) => {
    switch (method) {
        case "get_attendee_detail":
        return [];
        case "check_synchronization_status":
        return {};
        case "get_default_duration":
        return 3.25;
    }
});

onRpc("/calendar/check_credentials", async (args) => {
    return Promise.resolve(true);
});


test(`Check the avatar of the attendee in the calendar filter panel autocomplete`, async () => {
    await mountView(calendarFilterParams);

    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    expect(`.o_calendar_filter:eq(0) .o-autocomplete`).toHaveCount(1);
    expect('.o_calendar_filter_item:eq(-2)').not.toHaveText('partner 3');

    await click(".o-autocomplete input");
    await advanceTime(300);
    expect('.o-autocomplete--dropdown-item:first-child').toHaveText('partner 3');
    expect(`.o-autocomplete--dropdown-item:first-child .dropdown-item img`).toHaveClass('o_avatar');

    await contains(".o-autocomplete--dropdown-item:first-child").click();
    expect('.o_calendar_filter_item:eq(-2)').toHaveText('partner 3');
});


test(`Select multiple attendees in the calendar filter panel autocomplete`, async () => {
    onRpc("has_group", () => true);

    ResPartner._views = {
        list: `<tree><field name="name"/></tree>`,
        search: `<search/>`,
    };

    ResPartner._records.push(
        { id: 5, name: "foo partner 5" },
        { id: 6, name: "foo partner 6" },
        { id: 7, name: "foo partner 7" },
        { id: 8, name: "foo partner 8" },
        { id: 9, name: "foo partner 9" },
        { id: 10, name: "foo partner 10" },
        { id: 11, name: "foo partner 11" },
        { id: 12, name: "foo partner 12" },
        { id: 13, name: "foo partner 13" }
    );

    await mountView(calendarFilterParams);

    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    expect(`.o_calendar_filter_item`).toHaveCount(4);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "Mitchell Admin",
        "partner 1",
        "partner 2",
        "Everybody's calendars",
    ])

    expect(`.o_calendar_filter:eq(0) .o-autocomplete`).toHaveCount(1);
    await click(".o-autocomplete input");
    await advanceTime(300);
    expect(`.dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "partner 3",
        "partner 4",
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "Search More...",
    ]);

    await contains(`.o-autocomplete--dropdown-item:last-child`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_data_row`).toHaveCount(11);
    await contains(".o_data_row:nth-child(1) .o_list_record_selector").click();
    await contains(".o_data_row:nth-child(2) .o_list_record_selector").click();
    await contains(".o_dialog .o_select_button").click();
    expect("o_dialog").toHaveCount(0);


    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    expect(`.o_calendar_filter_item`).toHaveCount(6);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "Mitchell Admin",
        "partner 1",
        "partner 2",
        "partner 3",
        "partner 4",
        "Everybody's calendars",
    ])
});
