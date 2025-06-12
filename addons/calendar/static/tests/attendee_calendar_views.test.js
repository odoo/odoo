import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    contains,
    makeMockServer,
    MockServer,
    mountView,
    onRpc,
    preloadBundle,
    serverState,
} from "@web/../tests/web_test_helpers";
import {
    changeScale,
    clickEvent,
    expandCalendarView,
    findDateColumn,
    findTimeRow,
} from "@web/../tests/views/calendar/calendar_test_helpers";

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

const serverData = {};

const arch = /*xml*/ `
    <calendar js_class="attendee_calendar"
        event_open_popup="1"
        date_start="start"
        date_stop="stop"
        all_day="allday"
        mode="month"
    >
        <field name="partner_ids" options="{'block': True, 'icon': 'fa fa-users'}"
            filters="1" widget="many2manyattendeeexpandable" write_model="calendar.filters"
            write_field="partner_id" filter_field="partner_checked" avatar_field="avatar_128"/>
        <field name="partner_id" string="Organizer" options="{'icon': 'fa fa-user-o'}"/>
        <field name="user_id"/>
        <field name="start"/>
        <field name="stop"/>
        <field name="allday"/>
        <field name="res_model_name" invisible="not res_model_name"
            options="{'icon': 'fa fa-link', 'shouldOpenRecord': true}"/>
    </calendar>
`;

async function selectTimeStart(startDateTime) {
    const [startDate, startTime] = startDateTime.split(" ");
    const startCol = findDateColumn(startDate);
    const startRow = findTimeRow(startTime);
    await scrollTo(startRow);

    const startColRect = startCol.getBoundingClientRect();
    const startRowRect = startRow.getBoundingClientRect();
    await contains(startRow).click({
        position: {
            x: startColRect.x + startColRect.width / 2,
            y: startRowRect.y + 1,
        },
    });
}

beforeEach(async () => {
    mockDate("2016-12-12 08:00:00", 0);
    const { env: pyEnv } = await makeMockServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner 1" },
        { name: "Partner 2" },
    ]);
    serverData.partnerId_1 = partnerId_1;
    serverData.partnerId_2 = partnerId_2;
    serverData.userId = pyEnv["res.users"].create({ name: "User 1", partner_id: partnerId_1 });
    serverData.attendeeIds = pyEnv["calendar.attendee"].create([
        { partner_id: serverState.partnerId },
        { partner_id: partnerId_1 },
        { partner_id: partnerId_2 },
    ]);
    pyEnv["calendar.filters"].create([
        { partner_id: partnerId_1, partner_checked: true, user_id: serverState.userId },
        { partner_id: partnerId_2, partner_checked: true, user_id: serverData.userId },
    ]);
    pyEnv["calendar.event"].create([
        {
            name: "event 1",
            start: "2016-12-11 00:00:00",
            stop: "2016-12-11 01:00:00",
            attendee_ids: serverData.attendeeIds,
            partner_ids: [serverState.partnerId, partnerId_1, partnerId_2],
        },
        {
            name: "event 2",
            start: "2016-12-12 10:55:05",
            stop: "2016-12-12 14:55:05",
            attendee_ids: [serverData.attendeeIds[0], serverData.attendeeIds[1]],
            partner_ids: [serverState.partnerId, partnerId_1],
        },
    ]);
});

test("Linked record rendering", async () => {
    const pyEnv = MockServer.current.env;
    onRpc("res.users", "has_group", () => true);
    onRpc("res.users", "check_synchronization_status", () => ({}));
    onRpc("res.partner", "get_attendee_detail", () => []);
    onRpc("/calendar/check_credentials", () => ({}));
    const { id: modelId, display_name } = pyEnv["ir.model"].search_read(
        [["model", "=", "res.partner"]],
        ["display_name"]
    )[0];
    const eventId = pyEnv["calendar.event"].create({
        user_id: serverData.userId,
        name: "event With record",
        start: "2016-12-11 09:00:00",
        stop: "2016-12-11 10:00:00",
        attendee_ids: serverData.attendeeIds,
        partner_ids: [serverState.partnerId, serverData.partnerId_1, serverData.partnerId_2],
        res_model_id: modelId,
    });
    await mountView({ type: "calendar", resModel: "calendar.event", arch });
    expect(".o_calendar_renderer .fc-view").toHaveCount(1);

    await changeScale("week");
    await clickEvent(eventId);
    expect(".fa-link").toHaveCount(1, { message: "A link icon should be present" });
    expect("li a[href='#']").toHaveText(display_name);
});

test("Default duration rendering", async () => {
    onRpc("res.users", "has_group", () => true);
    onRpc("res.users", "check_synchronization_status", () => ({}));
    onRpc("res.partner", "get_attendee_detail", () => []);
    onRpc("/calendar/check_credentials", () => ({}));
    await mountView({ type: "calendar", resModel: "calendar.event", arch });
    expandCalendarView();
    await changeScale("week");
    await selectTimeStart("2016-12-15 15:00:00");
    await contains(".o-calendar-quick-create--input").edit("Event with new duration", {
        confirm: false,
    });
    await contains(".o-calendar-quick-create--create-btn").click();
    // This new event is the third
    await clickEvent(3);
    expect("div[name='start'] div").toHaveText("Dec 15, 3:00 PM");
    expect("div[name='stop'] div").toHaveText("Dec 15, 6:15 PM", {
        message: "The duration should be 3.25 hours",
    });
});
