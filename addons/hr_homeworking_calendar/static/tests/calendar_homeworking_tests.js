/** @odoo-module **/

import {
    click,
    getFixture, patchDate, patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import {
    patchAttendeeCalendarCommonPopover,
    patchAttendeeCalendarCommonPopoverClass
} from "@hr_homeworking_calendar/calendar/common/popover/calendar_common_popover";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";

const { DateTime, Interval } = luxon;
const mockRegistry = registry.category("mock_server");

let target;
let serverData;
const uid = 1;
const partnerId = 1;

const office = {
    location_type: 'office',
    location_name: 'Office',
    work_location_id: 1,
};
const home = {
    location_type: 'home',
    location_name: 'Home',
    work_location_id: 2,
};

const falseLocation = {
    location_type: false,
    location_name: false,
    work_location_id: false,
};

const multiCalendarData = {
    "1": {
        user_id: 1,
        employee_id: 1,
        partner_id: 1,
        employee_name: "Aaron",
        monday_location_id: office,
        tuesday_location_id: office,
        wednesday_location_id: home,
        thursday_location_id: falseLocation,
        friday_location_id: falseLocation,
        saturday_location_id: office,
        sunday_location_id: office,
    },
    "2": {
        user_id: 2,
        employee_id: 2,
        partner_id: 2,
        employee_name: "Brian",
        monday_location_id: home,
        tuesday_location_id: office,
        wednesday_location_id: home,
        thursday_location_id: home,
        friday_location_id: falseLocation,
        saturday_location_id: office,
        sunday_location_id: home,
    }
};

const singleCalendarData = {
    "1": multiCalendarData["1"],
};

async function createHomeWorkingView(serverData, workLocationMock) {
    mockRegistry.add("get_worklocation", () => {
        return workLocationMock;
    }, { force: true });
    await makeView({
        type: "calendar",
        resModel: "event",
        serverData,
        arch: `
            <calendar js_class="attendee_calendar" event_open_popup="1" date_start="start" date_stop="stop" all_day="allday">
                <field name="partner_ids" options="{'block': True, 'icon': 'fa fa-users'}" filters="1" write_model="filter_partner" write_field="partner_id" filter_field="partner_checked" avatar_field="avatar_128"/>
                <field name="partner_id" string="Organizer" options="{'icon': 'fa fa-user-o'}"/>
                <field name="user_id"/>
                <field name="start"/>
                <field name="stop"/>
                <field name="allday"/>
            </calendar>
        `,
        mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/res.users/has_group") {
                return Promise.resolve(true);
            } else if (route === "/web/dataset/call_kw/res.partner/get_attendee_detail") {
                return Promise.resolve([]);
            } else if (route === "/calendar/check_credentials") {
                return Promise.resolve({});
            } else if (route === "/web/dataset/call_kw/res.users/check_synchronization_status") {
                return Promise.resolve({});
            } else if (route === "/web/dataset/call_kw/event/get_state_selections") {
                return Promise.resolve([
                    ('needsAction', 'Needs Action'),
                    ('tentative', 'Maybe'),
                    ('declined', 'No'),
                    ('accepted', 'Yes'),
                ]);
            } else if (route === "/web/dataset/call_kw/calendar.event/get_default_duration") {
                return Promise.resolve(1);
            } else if (route === "/web/dataset/call_kw/res.users/read") {
                return Promise.resolve([{user : uid, can_edit: true}]);
            }
        },
    });
}

QUnit.module("Homeworking Calendar", ({ beforeEach }) => {
    beforeEach(() => {
        patchDate(2020, 11, 10, 15, 0, 0);
        target = getFixture();
        setupViewRegistries();
        patchWithCleanup(AttendeeCalendarCommonPopover.prototype, patchAttendeeCalendarCommonPopover);
        patchWithCleanup(AttendeeCalendarCommonPopover, patchAttendeeCalendarCommonPopoverClass);
        patchWithCleanup(user, {
            userId: uid,
            partnerId: partnerId,
        });

        serverData = {
            models: {
                event: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        user_id: {
                            string: "user",
                            type: "many2one",
                            relation: "user",
                            default: uid,
                        },
                        partner_id: {
                            string: "user",
                            type: "many2one",
                            relation: "partner",
                            related: "user_id.partner_id",
                            default: 1,
                        },
                        name: { string: "name", type: "char" },
                        start_date: { string: "start date", type: "date" },
                        stop_date: { string: "stop date", type: "date" },
                        start: { string: "start datetime", type: "datetime" },
                        stop: { string: "stop datetime", type: "datetime" },
                        delay: { string: "delay", type: "float" },
                        duration: { string: "Duration", type: "float", default: 1 },
                        allday: { string: "allday", type: "boolean" },
                        partner_ids: {
                            string: "attendees",
                            type: "one2many",
                            relation: "partner",
                            default: [[6, 0, [1]]],
                        },
                        type: { string: "type", type: "integer" },
                        event_type_id: {
                            string: "Event Type",
                            type: "many2one",
                            relation: "event_type",
                        },
                        color_event: {
                            string: "Color",
                            type: "integer",
                            related: "event_type_id.color_event_type",
                        },
                        is_hatched: { string: "Hatched", type: "boolean" },
                        is_striked: { string: "Striked", type: "boolean" },
                        res_model_name: { string: "Linked Model Name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 1",
                            start: "2016-12-11 00:00:00",
                            stop: "2016-12-11 01:00:00",
                            allday: false,
                            partner_ids: [1, 2, 3],
                            type: 1,
                            is_hatched: false,
                        },
                        {
                            id: 2,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 2",
                            start: "2016-12-12 10:55:05",
                            stop: "2016-12-12 14:55:05",
                            allday: false,
                            partner_ids: [1, 2],
                            type: 3,
                            is_hatched: false,
                        },
                    ],
                    methods: {
                        has_access() {
                            return Promise.resolve(true);
                        },
                    },
                },
                user: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Displayed name", type: "char" },
                        partner_id: {
                            string: "partner",
                            type: "many2one",
                            relation: "partner",
                        },
                        can_edit: { string: "User can edit his own record", type: "boolean"},
                    },
                    records: [
                        { id: 1, display_name: "user 1", partner_id: 1 , can_edit: true},
                        { id: 4, display_name: "user 4", partner_id: 4 },
                    ],
                },
                partner: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Displayed name", type: "char" },
                        image: { string: "image", type: "integer" },
                    },
                    records: [
                        { id: 1, display_name: "partner 1", image: "AAA" },
                        { id: 2, display_name: "partner 2", image: "BBB" },
                    ],
                },
                filter_partner: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        user_id: { string: "user", type: "many2one", relation: "user" },
                        partner_id: {
                            string: "partner",
                            type: "many2one",
                            relation: "partner",
                        },
                        partner_checked: { string: "checked", type: "boolean" },
                    },
                    records: [
                        { id: 1, user_id: uid, partner_id: 1, partner_checked: true },
                        { id: 2, user_id: uid, partner_id: 2, partner_checked: true },
                    ],
                },
                "hr.work.location": {
                    fields: {
                        id: { string: "ID", type: "integer"},
                        name: { string: "Name", type: "string"},
                        location_type: {
                            string: 'Location',
                            type: 'selection',
                            selection: [['home', "Home"], ['office', "Office"], ["other", "Other"]],
                        }
                    },
                    records: [
                        {
                            id: 1,
                            name: "Office",
                            location_type: "office",
                        },
                        {
                            id: 2,
                            name: "Home",
                            location_type: "home",
                        }
                    ]
                },
                "hr.employee": {
                    fields: {
                        id: { type: "integer"},
                        name: { string: "Name", type: "string" },
                        partner_id: { type: "many2one", relation: 'partner'}
                    },
                    records: [{id: 1, name: "Aaron", partner_id: 1}, {id: 2, name: "Brian", partner_id: 2}]
                }
            },
        };
    });

    QUnit.test(`homeworking: basic rendering`, async (assert) => {
        // Avoid `.o_worklocation_line` to have a width of `Opx`
        target.style.width = "1200px";

        assert.expect(7);
        const previousMock = mockRegistry.get("get_worklocation");
        const actionService = {
            start() {
                return {
                    doAction: (action, options) => {
                        assert.step(action);
                        assert.step(options.additionalContext.default_date);
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await createHomeWorkingView(serverData, singleCalendarData);
        const sundayDate = DateTime.fromISO("2020-12-06");
        const saturdayDate = DateTime.fromISO("2020-12-12");
        const intervals = Interval.fromDateTimes(sundayDate.startOf("day"), saturdayDate.endOf("day")).splitBy({day: 1});
        const workLocations = intervals.map(({s}) => {
            return target.querySelector(`.fc-col-header-cell[data-date="${s.toISODate()}"] .o_worklocation_btn`);
        });
        const worklocationNames = workLocations.map(el => el?.textContent);
        assert.deepEqual(worklocationNames, ["Office", "", "", "Home", "Set Location", "Set Location", "Office"]);

        await click(workLocations[0], '.o_worklocation_text');
        assert.equal(target.querySelector(".o_cw_popover div[name='employee_name']").textContent, "Aaron");
        assert.containsOnce(target, ".o_cw_popover .o_cw_popover_edit", "should show edit button");
        assert.containsOnce(target, ".o_cw_popover .o_cw_popover_delete", "should show delete button");

        await click(target.querySelector(".o_cw_popover_close"));
        await click(workLocations.at(-2), '.o_worklocation_line');
        assert.verifySteps(["hr_homeworking_calendar.set_location_wizard_action", "2020-12-11"]);
        mockRegistry.add("get_worklocation", previousMock, { force: true });
    });


    QUnit.test("homeworking: multicalendar", async function (assert) {
        assert.expect(16);
        const previousMock = mockRegistry.get("get_worklocation");
        await createHomeWorkingView(serverData, multiCalendarData);

        const sundayDate = DateTime.fromISO("2020-12-06");
        const saturdayDate = DateTime.fromISO("2020-12-12");
        const intervals = Interval.fromDateTimes(sundayDate.startOf("day"), saturdayDate.endOf("day")).splitBy({day: 1});
        intervals.forEach(({s}) => {
            const date = s.toISODate()
            const records = target.querySelectorAll(`.fc-col-header-cell[data-date="${date}"] .o_worklocation_btn .o_homeworking_content`);
            records.forEach(record => {
                const { employee, location } = record.dataset;
                assert.equal(multiCalendarData[employee][`${s.weekdayLong.toLowerCase()}_location_id`].location_type, location);
            });
        });

        assert.containsNone(target,'.fc-col-header-cell[data-date="2020-12-10"] .o_worklocation_text i .add_wl', "should show add work location button");
        assert.containsNone(target,'.fc-col-header-cell[data-date="2020-12-12"] .o_worklocation_text i .add_wl', "should not show add work location button");

        await click(target, '.fc-col-header-cell[data-date="2020-12-10"] .o_homework_content');
        assert.equal(target.querySelector(".o_cw_popover div[name='employee_name']").textContent, "Brian");
        assert.containsNone(target, ".o_cw_popover .o_cw_popover_edit", "should show edit button");
        assert.containsNone(target, ".o_cw_popover .o_cw_popover_delete", "should show delete button");
        await click(target.querySelector(".o_cw_popover_close"));

        mockRegistry.add("get_worklocation", previousMock, { force: true });
    });

    QUnit.test("homeworking: test exceptions are correctly rendered", async function (assert) {
        assert.expect(4);
        const previousMock = mockRegistry.get("get_worklocation");
        const actionService = {
            start() {
                return {
                    doAction: (action, options) => {
                        assert.step(action);
                        assert.step(options.additionalContext.default_date);
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });
        await createHomeWorkingView(serverData, {
            "1": {
                ...multiCalendarData["1"],
                exceptions: {
                    "2020-12-11": {
                        'hr_employee_location_id': 234,
                        ...home,
                    }
                }
            },
        });
        assert.equal(target.querySelector(".fc-col-header-cell[data-date='2020-12-11'] .o_worklocation_btn").textContent, "Home");
        await click(target, ".fc-col-header-cell[data-date='2020-12-10'] .o_worklocation_text");
        assert.verifySteps(["hr_homeworking_calendar.set_location_wizard_action", "2020-12-10"]);
        mockRegistry.add("get_worklocation", previousMock, { force: true });
    });

    QUnit.test("homeworking: test exceptions are correctly rendered in multicalendar", async function (assert) {
        assert.expect(8);
        const previousMock = mockRegistry.get("get_worklocation");
        const actionService = {
            start() {
                return {
                    doAction: (action, options) => {
                        assert.step(action);
                        assert.step(options.additionalContext.default_date);
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });
        await createHomeWorkingView(serverData, {
            1: {
                ...multiCalendarData[1],
                exceptions: {
                    "2020-12-10": {
                        'hr_employee_location_id': 3,
                        ...home,
                    }
                }
            },
            2: {
                ...multiCalendarData[2],
                exceptions: {
                    "2020-12-11": {
                        'hr_employee_location_id': 4,
                        ...office,
                    }
                }
            }
        });
        assert.containsOnce(target, ".fc-col-header-cell[data-date='2020-12-11'] .o_homework_content");
        assert.equal(target.querySelector(".fc-col-header-cell[data-date='2020-12-11'] .o_worklocation_btn").textContent, "Office");
        assert.containsN(target, ".fc-col-header-cell[data-date='2020-12-10'] .o_homework_content", 2);
        assert.equal(target.querySelector(".fc-col-header-cell[data-date='2020-12-10'] .o_worklocation_btn").textContent, "Home");
        assert.containsOnce(target, ".fc-col-header-cell[data-date='2020-12-11'] .add_wl");

        await click(target, ".fc-col-header-cell[data-date='2020-12-11'] .add_wl");
        assert.verifySteps(["hr_homeworking_calendar.set_location_wizard_action", "2020-12-11"]);
        mockRegistry.add("get_worklocation", previousMock, { force: true });
    });
});
