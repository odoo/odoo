import { expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, click, edit, runAllTimers } from "@odoo/hoot-dom";
import { serverState } from "@web/../tests/_framework/mock_server_state.hoot";
import { defineModels, onRpc } from "@web/../tests/_framework/mock_server/mock_server";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { contains, fields, models, preloadBundle } from "@web/../tests/web_test_helpers";
import { CalendarModel } from "@web/views/calendar/calendar_model";

class Event extends models.Model {
    name = fields.Char();
    date_start = fields.Date();
    type = fields.Many2one({ relation: "event.type" });
    user_id = fields.Many2one({ relation: "calendar.user" });
    filter_user_id = fields.Many2one({ relation: "calendar.user" });

    has_access() {
        return true;
    }

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
    ];

    _views = {
        calendar: `
            <calendar date_start="date_start" scales="month" multi_create_view="multi_create_form" aggregate="id:count">
                <!-- Popover -->
                <field name="name"/>
                <field name="type"/>
                
                <!-- Filter -->
                <field name="user_id" write_model="filter.user" write_field="filter_user_id" filter_field="is_checked"/>
            
                <!-- for filter to works -->
                <field name="date_start" invisible="1"/>
                <field name="filter_user_id" invisible="1"/>
            </calendar>
        `,
        "form,multi_create_form": `
            <form>
                <group>
                    <field name="name"/>
                    <field name="type"/>
                </group>
            </form>
        `,
    };
}

class EventType extends models.Model {
    name = fields.Char();
    color = fields.Integer();

    has_access() {
        return true;
    }

    _records = [
        { id: 1, name: "Event Type 1", color: 1 },
        { id: 2, name: "Event Type 2", color: 2 },
        { id: 3, name: "Event Type 3 (color 4)", color: 4 },
    ];
}

class CalendarUser extends models.Model {
    name = fields.Char();
    image = fields.Char();

    _records = [
        { id: 1, name: "user 1", image: "AAA" },
        { id: 2, name: "user 2", image: "BBB" },
        { id: 3, name: "user 3", image: "CCC" },
        { id: 4, name: "user 4", image: "DDD" },
        { id: 7, name: "user 7", image: "DDD" },
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

test("multi_create: render and basic functionalities", async () => {
    onRpc("event", "create", ({ args: [records] }) => {
        expect.step(records.length);
        for (const record of records) {
            if (record.name !== "Time off" || record.type !== 3) {
                expect.step("error");
            }
            expect.step(`${record.user_id}_${record.date_start}`);
        }
    });
    onRpc("event", "unlink", ({ args: [ids] }) => {
        expect.step(ids);
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        context: { default_name: "Sick" },
    });

    expect(".fc .fc-event").toHaveCount(4, { message: "events should be filter" });
    expect(".o_calendar_sidebar .btn-group .btn").toHaveCount(3, {
        message: "multi create should be enabled",
    });

    // Create mode
    expect(".o_calendar_sidebar .btn-group .btn.active").toHaveAttribute("data-tooltip", "New", {
        message: "multi create mode should be the default",
    });
    expect(".o_calendar_sidebar_container .o_form_view").toBeVisible();
    expect(".o_calendar_sidebar_container .o_form_view [name='name'] input").toHaveValue("Sick", {
        message: "should have a default value from the context",
    });
    await click(".o_calendar_sidebar_container .o_form_view [name='name'] input");
    await edit("Time off");
    await contains(".o_calendar_sidebar_container .o_form_view [name='type'] input").click();
    await contains(".o-autocomplete--dropdown-item:contains('Event Type 3 (color 4)')").click();

    const drag1 = await contains(".fc-day[data-date='2019-03-04']").drag();
    await drag1.moveTo(".fc-day[data-date='2019-03-28']");
    await animationFrame();
    expect(".fc-day.o-highlight").toHaveCount(16);
    await drag1.drop();
    await animationFrame();
    expect.verifySteps([
        32,
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
        "1_2019-03-18",
        "3_2019-03-18",
        "1_2019-03-19",
        "3_2019-03-19",
        "1_2019-03-20",
        "3_2019-03-20",
        "1_2019-03-21",
        "3_2019-03-21",
        "1_2019-03-25",
        "3_2019-03-25",
        "1_2019-03-26",
        "3_2019-03-26",
        "1_2019-03-27",
        "3_2019-03-27",
        "1_2019-03-28",
        "3_2019-03-28",
    ]);
    expect(".fc .fc-event").toHaveCount(36, {
        message: "events should be added for the two users selected",
    });

    await click(".fc-event[data-event-id='8']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .o_field_widget[name='name']").toHaveText("Time off");
    await expect(".o_popover .o_field_widget[name='type']").toHaveText("Event Type 3 (color 4)");
    await expect(".o_popover .o_field_widget[name='user_id']").toHaveText("user 1");

    await click(".fc-event[data-event-id='9']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);
    await expect(".o_popover .o_field_widget[name='user_id']").toHaveText("user 3");

    await click(".o_calendar_filter_item[data-value='3'] input");
    await animationFrame();
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    expect(".fc .fc-event").toHaveCount(18, { message: "events should be filter" });

    // Delete mode
    await click(".o_calendar_sidebar .btn-group .btn[data-tooltip='Delete']");
    await animationFrame();
    expect(".o_calendar_sidebar .btn-group .btn.active").toHaveAttribute("data-tooltip", "Delete", {
        message: "multi delete mode should be active",
    });
    expect(".o_calendar_sidebar_container .o_form_view").toHaveCount(0);

    await click(".fc-event[data-event-id='8']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);

    await click(".o_calendar_header");
    await animationFrame();

    const drag2 = await contains(".fc-day[data-date='2019-02-26']").drag();
    await drag2.drop(".fc-day[data-date='2019-04-03']");
    await animationFrame();
    expect.verifySteps([[10, 12, 2, 3, 18, 20, 26, 28, 34, 36]]);
    expect(".fc .fc-event").toHaveCount(8, { message: "selected events should be deleted" });

    await click(".o_calendar_filter_item[data-value='3'] input");
    await animationFrame();
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    expect(".fc .fc-event").toHaveCount(26, { message: "events should be filter" });

    // filter mode
    await click(".o_calendar_sidebar .btn-group .btn[data-tooltip='Filter']");
    await animationFrame();
    expect(".o_calendar_sidebar .btn-group .btn.active").toHaveAttribute("data-tooltip", "Filter", {
        message: "filter mode (normal) should be active",
    });

    await click(".fc-event[data-event-id='8']");
    await runAllTimers();
    await animationFrame();
    await expect(".o_popover").toHaveCount(1);

    await click(".o_calendar_header");
    await animationFrame();

    const drag3 = await contains(".fc-day[data-date='2019-02-26']").drag();
    await drag3.drop(".fc-day[data-date='2019-04-03']");
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal input[name='title']").toHaveValue("Sick");
});
