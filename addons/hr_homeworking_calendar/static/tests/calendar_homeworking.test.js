import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll, queryAllProperties, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { toggleFilter } from "@web/../tests/views/calendar/calendar_test_helpers";
import { contains, defineModels, fields, mockService, models, mountView, onRpc, serverState } from "@web/../tests/web_test_helpers";

const { DateTime, Interval } = luxon;

describe.current.tags("desktop");

class CalendarEvent extends models.Model {
    _records = [
        {
            id: 1,
            user_id: serverState.userId,
            partner_id: serverState.partnerId,
            name: "event 1",
            start: "2016-12-11 00:00:00",
            stop: "2016-12-11 01:00:00",
            allday: false,
            partner_ids: [models.Command.link(serverState.partnerId), models.Command.link(2), models.Command.link(3)],
        },
        {
            id: 2,
            user_id: serverState.userId,
            partner_id: serverState.partnerId,
            name: "event 2",
            start: "2016-12-12 10:55:05",
            stop: "2016-12-12 14:55:05",
            allday: false,
            partner_ids: [models.Command.link(serverState.partnerId), models.Command.link(2)],
        },
    ];

    user_id = fields.Many2one({ relation: "users" });
    partner_id = fields.Many2one({ relation: "partner" });
    name = fields.Char();
    start = fields.Datetime();
    stop = fields.Datetime();
    allday = fields.Boolean();
    partner_ids = fields.One2many({ relation: "partner" });
}

class CalendarFilter extends models.Model {
    _records = [
        { id: 1, user_id: serverState.userId, partner_id: serverState.partnerId, partner_checked: true },
        { id: 2, user_id: 2, partner_id: 2, partner_checked: true },
    ];

    user_id = fields.Many2one({ relation: "users" });
    partner_id = fields.Many2one({ relation: "partner" });
    partner_checked = fields.Boolean();
}

class HrEmployee extends models.Model {
    _records = [
        { id: 1, name: "Aaron", partner_id: serverState.partnerId },
        { id: 2, name: "Brian", partner_id: 2 },
    ];

    name = fields.Char();
    partner_id = fields.Many2one({ relation: "partner" });
}

class HrWorkLocation extends models.Model {
    _records = [
        { id: 1, name: "Office", location_type: "office" },
        { id: 2, name: "Home", location_type: "home" },
    ];

    name = fields.Char();
    location_type = fields.Selection({
        selection: [['home', "Home"], ['office', "Office"], ["other", "Other"]],
    });
}

class Partner extends models.Model {
    _records = [
        { id: serverState.partnerId, name: "Partner 1", image: "AAA" },
        { id: 2, name: "Partner 2", image: "BBB" },
        { id: 3, name: "Partner 3", image: "CCC" },
    ];

    name = fields.Char();
    image = fields.Binary();
}

class Users extends models.Model {
    _records = [
        { id: serverState.userId, name: "User 1", partner_id: serverState.partnerId },
        { id: 2, name: "User 2", partner_id: 2 },
    ];

    name = fields.Char();
    partner_id = fields.Many2one({ relation: "partner" });
}

defineModels([
    CalendarEvent,
    CalendarFilter,
    HrEmployee,
    HrWorkLocation,
    Partner,
    Users,
]);
defineMailModels();

onRpc("/calendar/check_credentials", async () => ({}));
onRpc("check_synchronization_status", async () => ({}));
onRpc("get_attendee_detail", () => []);
onRpc("get_default_duration", () => 1);
onRpc("get_state_selections", () => [
    ["accepted", "Yes"],
    ["declined", "No"],
    ["tentative", "Maybe"],
    ["needsAction", "Needs Action"],
]);
onRpc("res.users", "read", () => [{ user: serverState.userId }]);

beforeEach(() => {
    mockDate("2020-12-10 15:00:00");
});

const WORK_LOCATION_FALSE = {
    location_type: false,
    location_name: false,
    work_location_id: false,
};

const WORK_LOCATION_HOME = {
    location_type: "home",
    location_name: "Home",
    work_location_id: 2,
};

const WORK_LOCATION_OFFICE = {
    location_type: "office",
    location_name: "Office",
    work_location_id: 1,
};

const EMPLOYEE_WORK_LOCATIONS = {
    [1]: {
        user_id: serverState.userId,
        employee_id: 1,
        partner_id: serverState.partnerId,
        employee_name: "Aaron",
        monday_location_id: WORK_LOCATION_OFFICE,
        tuesday_location_id: WORK_LOCATION_OFFICE,
        wednesday_location_id: WORK_LOCATION_HOME,
        thursday_location_id: WORK_LOCATION_FALSE,
        friday_location_id: WORK_LOCATION_FALSE,
        saturday_location_id: WORK_LOCATION_OFFICE,
        sunday_location_id: WORK_LOCATION_OFFICE,
    },
    2: {
        user_id: 2,
        employee_id: 2,
        partner_id: 2,
        employee_name: "Brian",
        monday_location_id: WORK_LOCATION_HOME,
        tuesday_location_id: WORK_LOCATION_OFFICE,
        wednesday_location_id: WORK_LOCATION_HOME,
        thursday_location_id: WORK_LOCATION_HOME,
        friday_location_id: WORK_LOCATION_FALSE,
        saturday_location_id: WORK_LOCATION_OFFICE,
        sunday_location_id: WORK_LOCATION_HOME,
    },
};

function mountHomeWorkingView() {
    return mountView({
        type: "calendar",
        resModel: "calendar.event",
        arch: `
            <calendar js_class="attendee_calendar" event_open_popup="1" date_start="start" date_stop="stop" all_day="allday">
                <field name="partner_ids" options="{'block': True, 'icon': 'fa fa-users'}" filters="1" write_model="calendar.filter" write_field="partner_id" filter_field="partner_checked" avatar_field="avatar_128"/>
                <field name="partner_id" string="Organizer" options="{'icon': 'fa fa-user-o'}"/>
                <field name="user_id"/>
                <field name="start"/>
                <field name="stop"/>
                <field name="allday"/>
            </calendar>
        `,
    });
}

test(`basic rendering`, async () => {
    mockService("action", {
        async doAction(action, options) {
            expect.step([action, options?.additionalContext?.default_date]);
        },
    });
    onRpc("get_worklocation", () => ({ 1: EMPLOYEE_WORK_LOCATIONS[1] }));

    await mountHomeWorkingView();
    await toggleFilter("partner_ids", "2");

    const sundayDate = DateTime.fromISO("2020-12-06");
    const saturdayDate = DateTime.fromISO("2020-12-12");
    const intervals = Interval.fromDateTimes(sundayDate.startOf("day"), saturdayDate.endOf("day")).splitBy({ day: 1 });
    const workLocations = intervals.map(({ start }) => {
        return queryFirst(`.fc-col-header-cell[data-date="${start.toISODate()}"] .o_worklocation_btn`);
    });
    expect(queryAllTexts(workLocations)).toEqual(["Office", "", "", "Home", "Set Location", "Set Location", "Office"]);

    await contains(`.o_worklocation_text`, { root: workLocations[0] }).click();
    expect(`.o_cw_popover div[name="employee_name"]`).toHaveText("Aaron");
    expect(`.o_cw_popover .o_cw_popover_edit`).toHaveCount(1);
    expect(`.o_cw_popover .o_cw_popover_delete`).toHaveCount(1);

    await contains(`.o_cw_popover_close`).click();
    await contains(`.o_worklocation_line`, { root: workLocations.at(-2), visible: false }).click();
    expect.verifySteps([["hr_homeworking_calendar.set_location_wizard_action", "2020-12-11"]]);
});

test(`multicalendar`, async () => {
    onRpc("get_worklocation", () => EMPLOYEE_WORK_LOCATIONS);
    await mountHomeWorkingView();

    const sundayDate = DateTime.fromISO("2020-12-06");
    const saturdayDate = DateTime.fromISO("2020-12-12");
    const intervals = Interval.fromDateTimes(sundayDate.startOf("day"), saturdayDate.endOf("day")).splitBy({ day: 1 });

    const dataSetsByDates = intervals.map(({ start }) => queryAllProperties(`.fc-col-header-cell[data-date="${start.toISODate()}"] .o_worklocation_btn .o_homeworking_content`, "dataset"));
    const locations = dataSetsByDates.flatMap((dataSets) => dataSets.length ? dataSets.map((ds) => ds.location) : [false]);
    expect(locations).toEqual([
        "office", // sunday
        "home",   // sunday
        "office", // monday
        "home",   // monday
        "office", // tuesday
        "office", // tuesday
        "home",   // wednesday
        "home",   // wednesday
        "home",   // thursday
        false,    // friday
        "office", // saturday
        "office", // saturday
    ]);
    expect(queryAll(`.fc-col-header-cell[data-date="2020-12-10"] .o_worklocation_text i.add_wl`, { visible: false })).toHaveCount(1);
    expect(queryAll(`.fc-col-header-cell[data-date="2020-12-12"] .o_worklocation_text i.add_wl`, { visible: false })).toHaveCount(0);

    await contains(`.fc-col-header-cell[data-date="2020-12-10"] .o_homework_content`).click();
    expect(`.o_cw_popover div[name="employee_name"]`).toHaveText("Brian");
    expect(`.o_cw_popover .o_cw_popover_edit`).toHaveCount(0);
    expect(`.o_cw_popover .o_cw_popover_delete`).toHaveCount(0);
    await contains(`.o_cw_popover_close`).click();
});

test(`test exceptions are correctly rendered`, async () => {
    mockService("action", {
        async doAction(action, options) {
            expect.step([action, options?.additionalContext?.default_date]);
        },
    });
    onRpc("get_worklocation", () => ({
        1: {
            ...EMPLOYEE_WORK_LOCATIONS[1],
            exceptions: {
                "2020-12-11": {
                    hr_employee_location_id: 234,
                    ...WORK_LOCATION_HOME,
                },
            },
        },
    }));

    await mountHomeWorkingView();
    expect(`.fc-col-header-cell[data-date="2020-12-11"] .o_worklocation_btn`).toHaveText("Home");

    await contains(`.fc-col-header-cell[data-date="2020-12-10"] .o_worklocation_text`, { visible: false }).click();
    expect.verifySteps([["hr_homeworking_calendar.set_location_wizard_action", "2020-12-10"]]);
});

test(`test exceptions are correctly rendered in multicalendar`, async () => {
    mockService("action", {
        async doAction(action, options) {
            expect.step([action, options?.additionalContext?.default_date]);
        },
    });
    onRpc("get_worklocation", () => ({
        1: {
            ...EMPLOYEE_WORK_LOCATIONS[1],
            exceptions: {
                "2020-12-10": {
                    hr_employee_location_id: 3,
                    ...WORK_LOCATION_HOME,
                },
            },
        },
        2: {
            ...EMPLOYEE_WORK_LOCATIONS[2],
            exceptions: {
                "2020-12-11": {
                    hr_employee_location_id: 4,
                    ...WORK_LOCATION_OFFICE,
                },
            },
        },
    }));

    await mountHomeWorkingView();
    expect(`.fc-col-header-cell[data-date="2020-12-11"] .o_homework_content`).toHaveCount(1);
    expect(`.fc-col-header-cell[data-date="2020-12-11"] .o_worklocation_btn`).toHaveText("Office");
    expect(`.fc-col-header-cell[data-date="2020-12-10"] .o_homework_content`).toHaveCount(2);
    expect(`.fc-col-header-cell[data-date="2020-12-10"] .o_worklocation_btn`).toHaveText("Home");
    expect(queryAll(`.fc-col-header-cell[data-date="2020-12-11"] .add_wl`, { visible: false })).toHaveCount(1);

    await contains(`.fc-col-header-cell[data-date="2020-12-11"] .add_wl`, { visible: false }).click();
    expect.verifySteps([["hr_homeworking_calendar.set_location_wizard_action", "2020-12-11"]]);
});
