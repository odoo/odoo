import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";

import { clickAllDaySlot } from "@web/../tests/views/calendar/calendar_test_helpers";
import {
    contains,
    MockServer,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineAppointmentModels } from "./appointment_tests_common";

describe.current.tags("desktop");
defineAppointmentModels();

beforeEach(function () {
    mockDate("2022-01-05 00:00:00");
});

onRpc("/appointment/appointment_type/get_staff_user_appointment_types", function () {
    const domain = [
        ["staff_user_ids", "in", [100]],
        ["category", "!=", "custom"],
        ["website_published", "=", true],
    ];
    const appointment_types_info = this.env["appointment.type"].search_read(domain, [
        "category",
        "name",
    ]);

    return {
        appointment_types_info: appointment_types_info,
    };
});

onRpc("res.partner", "get_attendee_detail", () => []);

onRpc("res.users", "has_group", () => true);

onRpc("/calendar/check_credentials", () => ({}));

onRpc("calendar.event", "get_default_duration", () => 1);

onRpc("check_synchronization_status", () => ({}));

test("verify appointment links button are displayed", async () => {
    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                        js_class="attendee_calendar"
                        all_day="allday"
                        date_start="start"
                        date_stop="stop"
                        attendee="partner_ids">
                <field name="name"/>
                <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>`,
    });

    expect('button:contains("Share Availabilities")').toHaveCount(1);

    await contains(".dropdownAppointmentLink").click();

    expect('button:contains("Test Appointment")').toHaveCount(1);

    expect('button:contains("Propose Slots")').toHaveCount(1);

    expect('button:contains("Share Calendar")').toHaveCount(1);
});

test("create/search anytime appointment type", async () => {
    expect.assertions(6);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                expect(value).toBe(
                    `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${100}%5D`
                );
            },
        },
    });

    onRpc("/appointment/appointment_type/search_create_anytime", () => {
        expect.step("/appointment/appointment_type/search_create_anytime");
    });

    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                            js_class="attendee_calendar"
                            all_day="allday"
                            date_start="start"
                            date_stop="stop"
                            color="partner_id">
                    <field name="name"/>
                    <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
                </calendar>`,
        session: {
            "web.base.url": "http://amazing.odoo.com",
        },
    });
    await contains(".dropdownAppointmentLink").click();

    await contains(".o_appointment_search_create_anytime_appointment").click();
    await animationFrame();

    expect.verifySteps(["/appointment/appointment_type/search_create_anytime"]);
    expect(MockServer.env["appointment.type"]).toHaveLength(3, {
        message: "Create a new appointment type",
    });

    await contains(".o_appointment_discard_slots").click();
    await contains(".dropdownAppointmentLink").click();

    await contains(".o_appointment_search_create_anytime_appointment").click();
    await animationFrame();

    expect.verifySteps(["/appointment/appointment_type/search_create_anytime"]);
    expect(MockServer.env["appointment.type"]).toHaveLength(3, {
        message: "Does not create a new appointment type",
    });
});

test("discard slot in calendar", async () => {
    expect.assertions(11);

    onRpc("/appointment/appointment_type/search_create_anytime", () => {
        expect.step("/appointment/appointment_type/search_create_anytime");
    });

    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                        js_class="attendee_calendar"
                        all_day="allday"
                        date_start="start"
                        date_stop="stop">
                <field name="name"/>
                <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>`,
    });
    await contains(".o_calendar_filter_item[data-value=all] input").click();
    await contains(".o_appointment_select_slots").click();
    await animationFrame();
    expect('.o_appointment_scheduling_box b:contains("Pick your availabilities")').toHaveCount(1);

    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(0);
    // Same behavior as previous next button (+7 days)
    const currentDayPickerElement = queryOne(".o_datetime_picker .o_today.o_selected");
    const allPickerElement = [...currentDayPickerElement.parentElement.children];
    await contains(allPickerElement[allPickerElement.indexOf(currentDayPickerElement) + 7]).click();
    await animationFrame();
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(0);

    await clickAllDaySlot("2022-01-12");
    await animationFrame();
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(1);

    await contains("button.o_appointment_discard_slots").click();
    await animationFrame();
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(0);

    await contains(".o_calendar_button_today").click();
    await animationFrame();
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(0);
});

test("cannot move real event in slots-creation mode", async () => {
    expect.assertions(4);
    onRpc("write", () => {
        expect.step("write event");
    });

    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                        js_class="attendee_calendar"
                        all_day="allday"
                        date_start="start"
                        date_stop="stop">
                <field name="name"/>
                <field name="start"/>
                <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>`,
    });

    await contains(".o_calendar_filter_item[data-value=all] input").click();
    await contains(".o_appointment_select_slots").click();

    expect('.o_appointment_scheduling_box b:contains("Pick your availabilities")').toHaveCount(1);
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(0);
    await contains(".fc-event").dragAndDrop(".fc-day");
    await animationFrame();

    expect.verifySteps([]);
});

test("create slots for custom appointment type", async () => {
    expect.assertions(12);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                expect(value).toBe(
                    `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${100}%5D`
                );
            },
        },
    });
    onRpc("/appointment/appointment_type/create_custom", () => {
        expect.step("/appointment/appointment_type/create_custom");
    });

    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                            js_class="attendee_calendar"
                            all_day="allday"
                            date_start="start"
                            date_stop="stop">
                    <field name="name"/>
                    <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
                </calendar>`,
    });

    await contains(".o_calendar_filter_item[data-value=all] input").click();
    await contains(".o_appointment_select_slots").click();

    expect('.o_appointment_scheduling_box b:contains("Pick your availabilities")').toHaveCount(1);
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(0);

    // Same behavior as previous next button (+7 days)
    const currentDayPickerElement = queryOne(".o_datetime_picker .o_today.o_selected");
    const allPickerElement = [...currentDayPickerElement.parentElement.children];
    await contains(allPickerElement[allPickerElement.indexOf(currentDayPickerElement) + 7]).click();
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(0);

    await clickAllDaySlot("2022-01-12");
    await animationFrame();
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(1);

    await contains("button.o_appointment_get_link").click();
    expect.verifySteps(["/appointment/appointment_type/create_custom"]);
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(0);
    expect(MockServer.env["appointment.slot"]).toHaveLength(1);
});

test("filter works in slots-creation mode", async () => {
    expect.assertions(11);

    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                        js_class="attendee_calendar"
                        all_day="allday"
                        date_start="start"
                        date_stop="stop"
                        color="partner_id">
                <field name="name"/>
                <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>`,
    });

    await contains(".o_calendar_filter_item[data-value=all] input").click();
    // Two events are displayed
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(0);

    // Switch to slot-creation mode and create a slot for a custom appointment type
    await contains(".o_appointment_select_slots").click();

    expect('.o_appointment_scheduling_box b:contains("Pick your availabilities")').toHaveCount(1);

    // Same behavior as previous next button (+7 days)
    const currentDayPickerElement = queryOne(".o_datetime_picker .o_today.o_selected");
    const allPickerElement = [...currentDayPickerElement.parentElement.children];
    await contains(allPickerElement[allPickerElement.indexOf(currentDayPickerElement) + 7]).click();
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(0);

    await clickAllDaySlot("2022-01-12");
    await animationFrame();
    expect(".fc-event").toHaveCount(2);
    expect(".o_calendar_slot").toHaveCount(1);

    // Modify filters of the calendar to display less calendar event
    await contains(".o_calendar_filter_item:last-of-type > input").click();
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(1);

    await contains(".o_calendar_filter_item:last-of-type > input").click();
    await contains("button.o_appointment_discard_slots").click();
    expect(".fc-event").toHaveCount(1);
    expect(".o_calendar_slot").toHaveCount(0);
});

test("click & copy appointment type url", async () => {
    expect.assertions(2);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                expect(value).toBe(
                    `http://amazing.odoo.com/appointment/2?filter_staff_user_ids=%5B${100}%5D`
                );
            },
        },
    });

    onRpc("/appointment/appointment_type/get_book_url", () => {
        expect.step("/appointment/appointment_type/get_book_url");
    });

    await mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `<calendar class="o_calendar_test"
                            js_class="attendee_calendar"
                            all_day="allday"
                            date_start="start"
                            date_stop="stop"
                            color="partner_id">
                    <field name="name"/>
                    <field name="partner_ids" write_model="filter.partner" write_field="partner_id"/>
                </calendar>`,
    });

    await contains(".dropdownAppointmentLink").click();
    await contains(".o_appointment_appointment_link_clipboard").click();

    expect.verifySteps(["/appointment/appointment_type/get_book_url"]);
});
