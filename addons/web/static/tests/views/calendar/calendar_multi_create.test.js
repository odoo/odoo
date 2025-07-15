import { beforeEach, expect, test } from "@odoo/hoot";
import { click, edit, queryAllTexts } from "@odoo/hoot-dom";
import {
    advanceTime,
    animationFrame,
    disableAnimations,
    mockTimeZone,
    runAllTimers,
} from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    preloadBundle,
    serverState,
} from "@web/../tests/web_test_helpers";

import { CalendarModel } from "@web/views/calendar/calendar_model";
import { WebClient } from "@web/webclient/webclient";
import { notificationService } from "@web/core/notifications/notification_service";
import { markup } from "@odoo/owl";

class Event extends models.Model {
    name = fields.Char();
    date_start = fields.Date();
    datetime_start = fields.Datetime();
    datetime_end = fields.Datetime();
    type = fields.Many2one({ relation: "event.type" });
    user_id = fields.Many2one({ relation: "calendar.user" });
    user_ids = fields.Many2many({ relation: "calendar.user" });

    // FIXME: needed for the filter to work
    filter_user_id = fields.Many2one({ relation: "calendar.user" });

    _records = [
        {
            id: 1,
            name: "event 1",
            date_start: "2019-02-11",
            type: 1,
            user_id: 1,
        },
        {
            id: 2,
            name: "event 2",
            date_start: "2019-03-12",
            type: 1,
            user_id: 1,
        },
        {
            id: 3,
            name: "event 3",
            date_start: "2019-03-12",
            type: 1,
            user_id: 1,
        },
        {
            id: 4,
            name: "event 4",
            date_start: "2019-03-14",
            type: 1,
            user_id: 2,
        },
        {
            id: 5,
            name: "event 5",
            date_start: "2019-03-13",
            type: 1,
            user_id: 3,
        },
        {
            id: 6,
            name: "event 6",
            date_start: "2019-03-18",
            type: 1,
            user_id: 3,
        },
        {
            id: 7,
            name: "event 7",
            date_start: "2019-04-14",
            type: 1,
            user_id: 1,
        },
        {
            id: 8,
            name: "event 8",
            datetime_start: "2019-03-03 07:00:00",
            datetime_end: "2019-03-03 17:00:00",
            type: 1,
            user_id: 1,
        },
        {
            id: 9,
            name: "event 9",
            datetime_start: "2019-03-04 07:00:00",
            datetime_end: "2019-03-04 16:00:00",
            type: 1,
            user_id: 1,
        },
        {
            id: 10,
            name: "event 10",
            datetime_start: "2019-03-04 07:00:00",
            datetime_end: "2019-03-04 16:00:00",
            type: 1,
            user_id: 2,
        },
        {
            id: 11,
            name: "event 11",
            datetime_start: "2019-03-04 07:00:00",
            datetime_end: "2019-03-04 16:00:00",
            type: 1,
            user_id: 3,
        },
    ];

    _views = {
        calendar: `
            <calendar date_start="date_start" scales="month" multi_create_view="multi_create_form" aggregate="id:count">
                <!-- Popover -->
                <field name="name"/>
                <field name="type"/>
                
                <!-- Filter -->
                <field name="user_id" write_model="filter.user" write_field="filter_user_id" filter_field="is_checked"/>
            
                <!-- For filter to work -->
                <field name="date_start" invisible="1"/>
                <field name="filter_user_id" invisible="1"/>
            </calendar>
        `,
        "calendar,calendar_state": `
            <calendar date_start="datetime_start" date_stop="datetime_end" scales="month" multi_create_view="multi_create_form_state" aggregate="id:count">
                <!-- Popover -->
                <field name="name"/>
            </calendar>
        `,
        "form,multi_create_form": `
            <form>
                <group>
                    <field name="name" required="1"/>
                    <field name="type"/>
                </group>
            </form>
        `,
        "form,multi_create_form_state": `
            <form>
                <group>
                    <field name="name" required="1"/>
                    <field name="type"/>
                    <field name="user_ids" widget="many2many_tags"/>
                </group>
            </form>
        `,
    };
}

class EventType extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Event Type 1" },
        { id: 2, name: "Event Type 2" },
        { id: 3, name: "Event Type 3" },
    ];
}

class CalendarUser extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "user 1" },
        { id: 2, name: "user 2" },
        { id: 3, name: "user 3" },
        { id: 7, name: "user 7" },
    ];
}

class FilterUser extends models.Model {
    filter_user_id = fields.Many2one({ relation: "calendar.user" });
    user_id = fields.Many2one({ relation: "calendar.user" });
    is_checked = fields.Boolean();

    _records = [
        { id: 1, filter_user_id: 1, user_id: serverState.userId, is_checked: true },
        { id: 2, filter_user_id: 3, user_id: serverState.userId, is_checked: true },
    ];
}

defineModels([Event, EventType, CalendarUser, FilterUser]);

preloadBundle("web.fullcalendar_lib");

beforeEach(() => {
    mockTimeZone("Europe/Brussels");
    disableAnimations();
});

// Utils function

async function multiCreateClickAddButton() {
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
}

async function multiCreatePopoverClickAddButton() {
    await click(".o_multi_create_popover .popover-footer .btn:contains(Add)");
    await animationFrame();
}

test.tags("desktop");
test("multi_create: render and basic creation (simple use case)", async () => {
    onRpc("event", "create", ({ args: [records] }) => {
        for (const record of records) {
            expect.step(`${record.name}_${record.date_start}`);
        }
    });

    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar date_start="date_start" scales="month" multi_create_view="multi_create_form" aggregate="id:count">
            <!-- Popover -->
            <field name="name"/>
            <field name="date_start" invisible="1"/>
        </calendar>`,
    });

    expect(".fc .fc-event").toHaveCount(5, {
        message: "All events of this month should be visible",
    });
    expect(".o_calendar_filter_item").toHaveCount(0, {
        message: "No filters should be visible",
    });

    const { drop, moveTo } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await moveTo(".fc-day[data-date='2019-03-14']");
    await animationFrame();
    expect(".fc-day.o-highlight").toHaveCount(8);
    await drop();
    await animationFrame();

    expect(".o_selection_box").toHaveText("4\nselected");

    await multiCreateClickAddButton();
    expect(".o_multi_create_popover").toHaveCount(1);
    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await edit("Time off");
    await multiCreatePopoverClickAddButton();

    expect(".o_multi_create_popover").toHaveCount(0);
    expect.verifySteps([
        "Time off_2019-03-04",
        "Time off_2019-03-05",
        "Time off_2019-03-06",
        "Time off_2019-03-07",
        "Time off_2019-03-11",
        "Time off_2019-03-12",
        "Time off_2019-03-13",
        "Time off_2019-03-14",
    ]);
    expect(".fc .fc-event").toHaveCount(13, {
        message: "All new events should be added",
    });

    await click(".fc-event[data-event-id='12']");
    await runAllTimers();
    await animationFrame();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover .o_field_widget[name='name']").toHaveText("Time off");
});

test.tags("desktop");
test("multi_create: render and basic functionalities (complex with filters use case)", async () => {
    onRpc("event", "create", ({ args: [records] }) => {
        for (const record of records) {
            if (record.name !== "Time off" || record.type !== 3) {
                expect.step("error");
            }
            expect.step(`${record.user_id}_${record.date_start}`);
        }
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
    });

    expect(".fc .fc-event").toHaveCount(4, { message: "events should be filter" });

    const { drop, moveTo } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await moveTo(".fc-day[data-date='2019-03-14']");
    await animationFrame();
    expect(".fc-day.o-highlight").toHaveCount(8);
    await drop();
    await animationFrame();

    await multiCreateClickAddButton();

    expect(".o_multi_create_popover .o_form_view").toBeVisible();
    expect(".o_multi_create_popover .o_form_view [name='name'] input").toHaveValue("Sick", {
        message: "should have a default value from the context",
    });
    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await edit("Time off");
    await contains(".o_multi_create_popover .o_form_view [name='type'] input").click();
    await contains(".o-autocomplete--dropdown-item:contains('Event Type 3')").click();
    await multiCreatePopoverClickAddButton();

    expect.verifySteps([
        "1_2019-03-04",
        "3_2019-03-04",
        "1_2019-03-05",
        "3_2019-03-05",
        "1_2019-03-06",
        "3_2019-03-06",
        "1_2019-03-07",
        "3_2019-03-07",
        "1_2019-03-11",
        "3_2019-03-11",
        "1_2019-03-12",
        "3_2019-03-12",
        "1_2019-03-13",
        "3_2019-03-13",
        "1_2019-03-14",
        "3_2019-03-14",
    ]);
    expect(".fc .fc-event").toHaveCount(20, {
        message: "events should be added for the two users selected",
    });

    await click(".fc-event[data-event-id='12']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .o_field_widget[name='name']").toHaveText("Time off");
    await expect(".o_popover .o_field_widget[name='type']").toHaveText("Event Type 3");
    await expect(".o_popover .o_field_widget[name='user_id']").toHaveText("user 1");

    await click(".fc-event[data-event-id='13']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .o_field_widget[name='user_id']").toHaveText("user 3");

    await click(".o_calendar_filter_item[data-value='3'] input");
    await animationFrame();
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    expect(".fc .fc-event").toHaveCount(10, { message: "events should be filter" });
});

test.tags("desktop");
test("multi_create: basic creation (datetime field)", async () => {
    onRpc("event", "create", ({ args: [records] }) => {
        for (const record of records) {
            if (record.name !== "Time off" || record.type !== 3) {
                expect.step("error");
            }
            expect.step(`${record.user_id}_${record.datetime_start}_${record.datetime_end}`);
        }
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
        arch: `
            <calendar date_start="datetime_start" date_stop="datetime_end" scales="month" multi_create_view="multi_create_form" aggregate="id:count">
                <!-- Popover -->
                <field name="name"/>
                <field name="type"/>
                
                <!-- Filter -->
                <field name="user_id" write_model="filter.user" write_field="filter_user_id" filter_field="is_checked"/>
            </calendar>
        `,
    });

    expect(".fc .fc-event").toHaveCount(3, { message: "events should be filter" });

    const { drop, moveTo } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await moveTo(".fc-day[data-date='2019-03-14']");
    await animationFrame();
    expect(".fc-day.o-highlight").toHaveCount(8);
    await drop();
    await animationFrame();

    await multiCreateClickAddButton();

    expect(".o_multi_create_popover .o_time_picker_input").toHaveCount(2);

    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(1);
    await click(".o_time_picker_option:contains(8:00)");
    await animationFrame();

    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(1);
    await click(".o_time_picker_option:contains(11:30)");
    await animationFrame();

    expect(".o_multi_create_popover .o_form_view").toBeVisible();
    expect(".o_multi_create_popover .o_form_view [name='name'] input").toHaveValue("Sick", {
        message: "should have a default value from the context",
    });
    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await edit("Time off");
    await contains(".o_multi_create_popover .o_form_view [name='type'] input").click();
    await contains(".o-autocomplete--dropdown-item:contains('Event Type 3')").click();

    await multiCreatePopoverClickAddButton();

    expect.verifySteps([
        "1_2019-03-04 07:00:00_2019-03-04 10:30:00",
        "3_2019-03-04 07:00:00_2019-03-04 10:30:00",
        "1_2019-03-05 07:00:00_2019-03-05 10:30:00",
        "3_2019-03-05 07:00:00_2019-03-05 10:30:00",
        "1_2019-03-06 07:00:00_2019-03-06 10:30:00",
        "3_2019-03-06 07:00:00_2019-03-06 10:30:00",
        "1_2019-03-07 07:00:00_2019-03-07 10:30:00",
        "3_2019-03-07 07:00:00_2019-03-07 10:30:00",
        "1_2019-03-11 07:00:00_2019-03-11 10:30:00",
        "3_2019-03-11 07:00:00_2019-03-11 10:30:00",
        "1_2019-03-12 07:00:00_2019-03-12 10:30:00",
        "3_2019-03-12 07:00:00_2019-03-12 10:30:00",
        "1_2019-03-13 07:00:00_2019-03-13 10:30:00",
        "3_2019-03-13 07:00:00_2019-03-13 10:30:00",
        "1_2019-03-14 07:00:00_2019-03-14 10:30:00",
        "3_2019-03-14 07:00:00_2019-03-14 10:30:00",
    ]);
    expect(".fc .fc-event").toHaveCount(19, {
        message: "events should be added for the two users selected",
    });

    await click(".fc-event[data-event-id='12']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .fa-clock-o").toHaveCount(1);
    await expect(".o_popover .list-group-item:has(.fa-clock-o)").toHaveText(
        "08:00 - 11:30 (3 hours, 30 minutes)"
    );
    await expect(".o_popover .o_field_widget[name='name']").toHaveText("Time off");
    await expect(".o_popover .o_field_widget[name='type']").toHaveText("Event Type 3");
    await expect(".o_popover .o_field_widget[name='user_id']").toHaveText("user 1");

    await click(".fc-event[data-event-id='13']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .fa-clock-o").toHaveCount(1);
    await expect(".o_popover .list-group-item:has(.fa-clock-o)").toHaveText(
        "08:00 - 11:30 (3 hours, 30 minutes)"
    );
    await expect(".o_popover .o_field_widget[name='user_id']").toHaveText("user 3");

    await click(".o_calendar_filter_item[data-value='3'] input");
    await animationFrame();
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    expect(".fc .fc-event").toHaveCount(10, { message: "events should be filter" });
});

test.tags("desktop");
test("multi_create: input validation (datetime field)", async () => {
    patchWithCleanup(notificationService, {
        start: () => ({
            add: (message) => {
                expect.step(message);
            },
        }),
    });

    onRpc("event", "create", ({ args: [records] }) => {
        for (const record of records) {
            expect.step(`${record.user_id}_${record.datetime_start}_${record.datetime_end}`);
        }
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
        arch: `
            <calendar date_start="datetime_start" date_stop="datetime_end" scales="month" multi_create_view="multi_create_form" aggregate="id:count">
                <!-- Popover -->
                <field name="name"/>
                <field name="type"/>
                
                <!-- Filter -->
                <field name="user_id" write_model="filter.user" write_field="filter_user_id" filter_field="is_checked"/>
            </calendar>
        `,
    });

    const { drop } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await animationFrame();
    await drop();
    await animationFrame();

    await multiCreateClickAddButton();

    // No time range
    await click(".o_time_picker_input:eq(1)");
    await edit("", { confirm: "enter" });

    await multiCreatePopoverClickAddButton();

    expect.verifySteps(["Invalid time range"]);

    await multiCreateClickAddButton();
    // Start time before end time
    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    await click(".o_time_picker_option:contains(11:30)");
    await animationFrame();

    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    await click(".o_time_picker_option:contains(8:00)");
    await animationFrame();

    await multiCreatePopoverClickAddButton();

    expect.verifySteps(["Start time should be before end time"]);

    // Valid input
    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    await click(".o_time_picker_option:contains(12:00)");
    await animationFrame();

    await multiCreatePopoverClickAddButton();

    expect.verifySteps([
        "1_2019-03-04 10:30:00_2019-03-04 11:00:00",
        "3_2019-03-04 10:30:00_2019-03-04 11:00:00",
    ]);
});

// Test skipped has the state is push only when we add at least one record
// The state should be always accessible also before creating a record
test.tags("desktop");
test("multi_create: use state to keep values of inputs", async () => {
    onRpc("event.type", "get_formview_action", ({ args, model }) => ({
        type: "ir.actions.act_window",
        res_model: model,
        target: "current",
        views: [[false, "form"]],
        res_id: args[0][0],
    }));

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Event",
        res_model: "event",
        type: "ir.actions.act_window",
        views: [["calendar_state", "calendar"]],
    });

    let { drop } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await animationFrame();
    await drop();
    await animationFrame();

    await multiCreateClickAddButton();

    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    await click(".o_time_picker_option:contains(1:30)");
    await animationFrame();

    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    await click(".o_time_picker_option:contains(8:00)");
    await animationFrame();

    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await animationFrame();
    await edit("Test state");

    await contains(".o_multi_create_popover .o_form_view [name='type'] input").click();
    await contains(".o-autocomplete--dropdown-item:contains('Event Type 3')").click();

    await contains(".o_multi_create_popover .o_form_view [name='user_ids'] input").click();
    await contains(".o-autocomplete--dropdown-item:contains('user 1')").click();
    await contains(".o_multi_create_popover .o_form_view [name='user_ids'] input").click();
    await contains(".o-autocomplete--dropdown-item:contains('user 3')").click();

    // Navigate to the many2one record
    await click(".o_form_view [name='type'] .o_external_button");
    await animationFrame();
    await animationFrame();

    // Go back to the calendar view
    await click(".breadcrumb-item");
    await animationFrame();

    ({ drop } = await contains(".fc-day[data-date='2019-03-04']").drag());
    await animationFrame();
    await drop();
    await animationFrame();

    await multiCreateClickAddButton();

    expect(".o_time_picker_input:eq(0)").toHaveValue("1:30");
    expect(".o_time_picker_input:eq(1)").toHaveValue("8:00");
    expect(".o_form_view [name='name'] input").toHaveValue("Test state");
    expect(".o_form_view [name='type'] input").toHaveValue("Event Type 3");
    expect(queryAllTexts(".o_form_view [name='user_ids'] .o_tag")).toEqual(["user 1", "user 3"]);
});

test.tags("desktop");
test("multi_create: delete", async () => {
    onRpc("event", "unlink", ({ args: [ids] }) => {
        expect.step(ids);
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
    });

    await click(".fc-event[data-event-id='2']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);

    await click(".o_calendar_header"); // Hide the popover
    await animationFrame();

    const { drop } = await contains(".fc-day[data-date='2019-02-26']").drag();
    await drop(".fc-day[data-date='2019-04-03']");
    await animationFrame();

    await click(".o_multi_selection_buttons .btn .fa-trash");
    await animationFrame();

    expect.verifySteps([[2, 3, 5]]);
    expect(".fc .fc-event").toHaveCount(1, { message: "selected events should be deleted" });

    await click(".o_calendar_filter_item[data-value='3'] input");
    await animationFrame();
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    expect(".fc .fc-event").toHaveCount(0, { message: "events should be filter" });
});

test.tags("desktop");
test("multi_create: test onChange on form with no blur (input text)", async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
    });

    await click(".fc-day[data-date='2019-03-04']");
    await animationFrame();

    await multiCreateClickAddButton();

    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await edit("Test onChange");

    await multiCreatePopoverClickAddButton();

    await click(".fc-event[data-event-id='12']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .o_field_widget[name='name']").toHaveText("Test onChange");
});

test.tags("desktop");
test("multi_create: test onChange on TimePicker with no blur (input text)", async () => {
    patchWithCleanup(notificationService, {
        start: () => ({
            add: (message) => {
                expect.step(message);
            },
        }),
    });

    onRpc("event", "create", ({ args: [records] }) => {
        for (const record of records) {
            expect.step(`${record.user_id}_${record.datetime_start}_${record.datetime_end}`);
        }
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
        arch: `
            <calendar date_start="datetime_start" date_stop="datetime_end" scales="month" multi_create_view="multi_create_form" aggregate="id:count">
                <!-- Popover -->
                <field name="name"/>
                <field name="type"/>
                
                <!-- Filter -->
                <field name="user_id" write_model="filter.user" write_field="filter_user_id" filter_field="is_checked"/>
            </calendar>
        `,
    });

    const { drop } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await animationFrame();
    await drop();
    await animationFrame();

    await multiCreateClickAddButton();

    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await edit("Test onChange");

    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    await click(".o_time_picker_option:contains(1:30)");
    await animationFrame();

    await click(".o_time_picker_input:eq(1)");
    await animationFrame();
    await edit("8:00");
    await animationFrame();

    await multiCreatePopoverClickAddButton();

    expect.verifySteps([
        "1_2019-03-04 00:30:00_2019-03-04 07:00:00",
        "3_2019-03-04 00:30:00_2019-03-04 07:00:00",
    ]);
});

test.tags("desktop");
test("multi_create: test popover", async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
    });

    expect(".o_popover").toHaveCount(0);

    await click(".fc-event[data-event-id='2']");
    await runAllTimers();
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
});

test.tags("desktop");
test("multi_create: avoid trigger add/del event on specific element", async () => {
    function makeEvents(numberOfEvent) {
        return [...Array(numberOfEvent).keys()].map((i) => ({
            id: i,
            name: `event ${i}`,
            date_start: "2019-03-13",
            type: 1,
            user_id: 1,
        }));
    }
    Event._records = makeEvents(6);

    await mountView({
        resModel: "event",
        type: "calendar",
    });

    await click(".fc-event[data-event-id='1']");
    await runAllTimers();
    await animationFrame();
    expect(".o_popover").toHaveCount(1);

    await click(".o_calendar_button_today");
    await runAllTimers();
    await animationFrame();
    expect(".o_popover").toHaveCount(0);

    await click(".fc-more-cell a");
    await animationFrame();
    expect(".fc-more-popover").toHaveCount(1);
    expect(".o_multi_selection_buttons").toHaveCount(0);

    await click(".fc-popover-title");
    await animationFrame();
    expect(".fc-more-popover").toHaveCount(1);
    expect(".o_multi_selection_buttons").toHaveCount(0);

    await click(".fc-popover-close");
    await animationFrame();
    expect(".fc-more-popover").toHaveCount(0);
    expect(".o_multi_selection_buttons").toHaveCount(0);
});

test.tags("desktop");
test("multi_create: test required attribute in form", async () => {
    patchWithCleanup(notificationService, {
        start: () => ({
            add: (message) => {
                expect.step(message);
            },
        }),
    });

    onRpc("event", "create", ({ args: [records] }) => {
        for (const record of records) {
            expect.step(`${record.name}_${record.date_start}`);
        }
    });

    await mountView({
        resModel: "event",
        type: "calendar",
    });

    const { drop } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await animationFrame();
    await drop();
    await animationFrame();
    await multiCreateClickAddButton();
    await multiCreatePopoverClickAddButton();
    expect(".o_multi_create_popover .o_form_view [name='name']").toHaveClass("o_required_modifier");
    expect.verifySteps([markup`<ul><li>Name</li></ul>`]);

    const { drop: dropOk } = await contains(".fc-day[data-date='2019-03-04']").drag();
    await animationFrame();
    await dropOk();
    await animationFrame();
    await multiCreateClickAddButton();
    await click(".o_multi_create_popover .o_form_view [name='name'] input");
    await edit("Test required");
    await multiCreatePopoverClickAddButton();
    expect.verifySteps(["Test required_2019-03-04", "Test required_2019-03-04"]);
});
