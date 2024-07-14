/** @odoo-module **/

import { click, nextTick, getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { clickAllDaySlot } from "@web/../tests/views/calendar/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import testUtils from '@web/../tests/legacy/helpers/test_utils';
import { getServerModels } from "./appointment_tests_common";

const { DateTime } = luxon;
const serviceRegistry = registry.category("services");
const mockRegistry = registry.category("mock_server");

let target;
let serverData;
const uid = 1;
let appointmentMock;

QUnit.module('appointment.appointment_link', {
    before: function () {
        appointmentMock = mockRegistry.get("/appointment/appointment_type/get_staff_user_appointment_types");
        mockRegistry.add("/appointment/appointment_type/get_staff_user_appointment_types", function (route, args) {
            if (route === "/appointment/appointment_type/get_staff_user_appointment_types") {
                const domain = [
                    ['staff_user_ids', 'in', [1]],
                    ['category', '!=', 'custom'],
                    ['website_published', '=', true],
                ];
                const appointment_types_info = this.mockSearchRead('appointment.type', [domain, ['category', 'name']], {});

                return Promise.resolve({
                    appointment_types_info: appointment_types_info
                });
            }
        }, { force: true });
    },
    beforeEach: function () {
        serverData = {
            models: {
                ...getServerModels(DateTime.now().plus({ year: 1 }).year),
                'appointment.slot': {
                    fields: {
                        appointment_type_id: {type: 'many2one', relation: 'appointment.type'},
                        start_datetime: {string: 'Start', type: 'datetime'},
                        end_datetime: {string: 'End', type: 'datetime'},
                        duration: {string: 'Duration', type: 'float'},
                        slot_type: {
                            string: 'Slot Type',
                            type: 'selection',
                            selection: [['recurring', 'Recurring'], ['unique', 'One Shot']],
                        },
                    },
                },
                'filter_partner': {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        user_id: {string: "user", type: "many2one", relation: 'res.users'},
                        partner_id: {string: "partner", type: "many2one", relation: 'res.partner'},
                        partner_checked: {string: "checked", type: "boolean"},
                    },
                    records: [
                        {
                            id: 4,
                            user_id: uid,
                            partner_id: uid,
                            partner_checked: true
                        }, {
                            id: 5,
                            user_id: 214,
                            partner_id: 214,
                            partner_checked: true,
                        }
                    ]
                },
            },
            views: {},
        };
        patchDate(DateTime.now().plus({years:1}).year, 0, 5, 0, 0, 0);
        target = getFixture();
        setupViewRegistries();
        serviceRegistry.add(
            "user",
            {
                ...userService,
                start() {
                    const fakeUserService = userService.start(...arguments);
                    Object.defineProperty(fakeUserService, "userId", {
                        get: () => uid,
                    });
                    return fakeUserService;
                },
            },
            { force: true }
        );
    },
    after: function () {
        mockRegistry.add("/appointment/appointment_type/get_staff_user_appointment_types", appointmentMock, { force: true });
    }
}, function () {

QUnit.test('verify appointment links button are displayed', async function (assert) {
    assert.expect(3);

    await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    attendee="partner_ids">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
            <field name="partner_id" filters="1" invisible="1"/>
        </calendar>`,
        mockRPC: async function (route, args) {
            if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
    });

    assert.containsOnce(target, 'button:contains("Share Availabilities")');

    await click(target, '.dropdownAppointmentLink');

    assert.containsOnce(target, 'button:contains("Test Appointment")');

    assert.containsOnce(target, 'button:contains("Any Time")');
});

QUnit.test('create/search anytime appointment type', async function (assert) {
    assert.expect(9);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                assert.strictEqual(
                    value,
                    `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${uid}%5D`
                );
            }
        },
    });

    await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === "/appointment/appointment_type/search_create_anytime") {
                assert.step(route);
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
        session: {
            'web.base.url': 'http://amazing.odoo.com',
        },
    });

    assert.strictEqual(2, serverData.models['appointment.type'].records.length)

    await click(target.querySelector('.dropdownAppointmentLink'));

    await click(target.querySelector('.o_appointment_search_create_anytime_appointment'));
    await nextTick();

    assert.verifySteps(['/appointment/appointment_type/search_create_anytime']);
    assert.strictEqual(3, serverData.models['appointment.type'].records.length,
        "Create a new appointment type")

    await click(target.querySelector('.o_appointment_discard_slots'));
    await click(target.querySelector('.dropdownAppointmentLink'));

    await click(target.querySelector('.o_appointment_search_create_anytime_appointment'));
    await nextTick();

    assert.verifySteps(['/appointment/appointment_type/search_create_anytime']);
    assert.strictEqual(3, serverData.models['appointment.type'].records.length,
        "Does not create a new appointment type");
});

QUnit.test('discard slot in calendar', async function (assert) {
    assert.expect(11);

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: async function (route, args) {
            if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    await click(target.querySelector('.o_appointment_select_slots'));
    await nextTick();

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');
    
    // Same behavior as previous next button (+7 days)
    const currentDayPickerElement = target.querySelector('.o_datetime_picker .o_today.o_selected');
    const allPickerElement = [...currentDayPickerElement.parentElement.children]
    await click(allPickerElement[allPickerElement.indexOf(currentDayPickerElement) + 7]);    
    await nextTick();
    assert.containsOnce(target, '.fc-event', 'There is one calendar event');
    assert.containsNone(target, '.o_calendar_slot', 'There is no slot yet');

    await clickAllDaySlot(target, DateTime.now().toFormat("yyyy'-01-12'"));
    await nextTick();
    assert.containsN(target, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(target, '.o_calendar_slot', 'One of them is a slot');

    await click(target.querySelector('button.o_appointment_discard_slots'));
    await nextTick();
    assert.containsOnce(target, '.fc-event', 'The calendar event is still here');
    assert.containsNone(target, '.o_calendar_slot', 'The slot has been discarded');

    await click(target.querySelector('.o_calendar_button_today'));
    await nextTick();
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');
});

QUnit.test("cannot move real event in slots-creation mode", async function (assert) {
    assert.expect(4);

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="start"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (args.method === "write") {
                assert.step('write event');
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    await click(target.querySelector('.o_appointment_select_slots'));

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');

    await testUtils.dom.dragAndDrop($(target.querySelector('.fc-event')), $(target.querySelector('.fc-day')));
    await nextTick();

    assert.verifySteps([]);
});

QUnit.test("create slots for custom appointment type", async function (assert) {
    assert.expect(13);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                assert.strictEqual(
                    value,
                    `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${uid}%5D`
                );
            }
        }
    });

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === "/appointment/appointment_type/create_custom") {
                assert.step(route);
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    await click(target.querySelector('.o_appointment_select_slots'));

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');
    
    // Same behavior as previous next button (+7 days)
    const currentDayPickerElement = target.querySelector('.o_datetime_picker .o_today.o_selected');
    const allPickerElement = [...currentDayPickerElement.parentElement.children]
    await click(allPickerElement[allPickerElement.indexOf(currentDayPickerElement) + 7]); 
    assert.containsOnce(target, '.fc-event', 'There is one calendar event');
    assert.containsNone(target, '.o_calendar_slot', 'There is no slot yet');

    await clickAllDaySlot(target, DateTime.now().toFormat("yyyy'-01-12'"));
    await nextTick();
    assert.containsN(target, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(target, '.o_calendar_slot', 'One of them is a slot');

    await click(target.querySelector('button.o_appointment_get_link'));
    assert.verifySteps(['/appointment/appointment_type/create_custom']);
    assert.containsOnce(target, '.fc-event', 'The calendar event is still here');
    assert.containsNone(target, '.o_calendar_slot', 'The slot has been cleared after the creation');
    assert.strictEqual(serverData.models['appointment.slot'].records.length, 1);
});

QUnit.test('filter works in slots-creation mode', async function (assert) {
    assert.expect(11);

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
            <field name="partner_id" filters="1" invisible="1"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    // Two events are displayed
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');

    // Switch to slot-creation mode and create a slot for a custom appointment type
    await click(target.querySelector('.o_appointment_select_slots'));

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");

    // Same behavior as previous next button (+7 days)
    const currentDayPickerElement = target.querySelector('.o_datetime_picker .o_today.o_selected');
    const allPickerElement = [...currentDayPickerElement.parentElement.children]
    await click(allPickerElement[allPickerElement.indexOf(currentDayPickerElement) + 7]); 
    assert.containsOnce(target, '.fc-event');
    assert.containsNone(target, '.o_calendar_slot');

    await clickAllDaySlot(target, DateTime.now().toFormat("yyyy'-01-12'"));
    await nextTick();
    assert.containsN(target, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(target, '.o_calendar_slot', 'One of them is a slot');

    // Modify filters of the calendar to display less calendar event
    await click(target.querySelector('.o_calendar_filter_item:last-of-type > input'));
    assert.containsOnce(target, '.fc-event', 'There is now only 1 events displayed');
    assert.containsOnce(target, '.o_calendar_slot', 'The slot created is still displayed');

    await click(target.querySelector('.o_calendar_filter_item:last-of-type > input'));
    await click(target.querySelector('button.o_appointment_discard_slots'));
    assert.containsOnce(target, '.fc-event', 'There is now only 1 calendar event displayed');
    assert.containsNone(target, '.o_calendar_slot', 'There is no more slots in the calendar view');
});

QUnit.test('click & copy appointment type url', async function (assert) {
    assert.expect(3);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                assert.strictEqual(
                    value,
                    `http://amazing.odoo.com/appointment/2?filter_staff_user_ids=%5B${uid}%5D`
                );
            }
        }
    });

    await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === '/appointment/appointment_type/get_book_url') {
                assert.step(route)
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                return Promise.resolve(true);
            } else if (route === '/calendar/check_credentials') {
                return Promise.resolve({});
            }
        },
    });

    await click(target.querySelector('.dropdownAppointmentLink'));
    await click(target.querySelector('.o_appointment_appointment_link_clipboard'));

    assert.verifySteps(['/appointment/appointment_type/get_book_url']);
});
});
