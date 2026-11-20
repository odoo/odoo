import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    contains,
    editSearch,
    getService,
    makeMockServer,
    MockServer,
    mountView,
    mountWithCleanup,
    onRpc,
    preloadBundle,
    serverState,
    validateSearch,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

const serverData = {};

const arch = /* xml */ `
    <list js_class="calendar_list_view">
        <field name="name"/>
    </list>
`;

beforeEach(async () => {
    const { env: pyEnv } = await makeMockServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner 1" },
        { name: "Partner 2" },
    ]);
    serverData.partnerId_1 = partnerId_1;
    serverData.partnerId_2 = partnerId_2;
    // Partner 1 is the only attendee selected in the calendar view's sidebar.
    pyEnv["calendar.filters"].create([
        { partner_id: partnerId_1, active: true, user_id: serverState.userId },
        { partner_id: partnerId_2, active: false, user_id: serverState.userId },
    ]);
    pyEnv["calendar.event"].create([
        { name: "Meeting 1", partner_ids: [partnerId_1] },
        { name: "Meeting 2", partner_ids: [partnerId_2] },
    ]);
    onRpc("get_selected_calendars_partner_ids", () => {
        expect.step("get_selected_calendars_partner_ids");
    });
    onRpc("web_search_read", ({ kwargs }) => {
        expect.step(kwargs.domain);
    });
});

test("keep selected attendees when searching", async () => {
    await mountView({
        type: "list",
        resModel: "calendar.event",
        arch,
        globalState: { calendarFilters: { all: false, user: true } },
        searchViewArch: `
            <search>
                <field name="name" filter_domain="[('name', 'ilike', self)]"/>
            </search>
        `,
    });
    const attendeeDomain = ["partner_ids", "in", [serverData.partnerId_1, serverState.partnerId]];
    expect.verifySteps(["get_selected_calendars_partner_ids", [attendeeDomain]]);

    await editSearch("Meeting 2");
    await validateSearch();
    expect.verifySteps([[["name", "ilike", "Meeting 2"], attendeeDomain]]);
    expect(".o_data_row").toHaveCount(0);
});

test("do not apply selected attendees when the action has a domain", async () => {
    const domain = [["name", "=", "Meeting 2"]];
    await mountView({
        type: "list",
        resModel: "calendar.event",
        arch,
        domain,
        globalState: { calendarFilters: { all: false, user: true } },
    });
    expect.verifySteps([domain]);
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_cell[name='name']").toHaveText("Meeting 2");
});

test.tags("desktop");
test("keep selected attendees when switching from the calendar view", async () => {
    mockDate("2016-12-12 08:00:00", 0);
    onRpc("res.users", "has_group", () => true);
    onRpc("res.partner", "get_attendee_detail", () => []);
    onRpc("res.users", "get_calendar_model_data", () => ({
        credential_status: {},
        sync_status: {},
        sync_email: false,
        default_duration: 1,
    }));
    const pyEnv = MockServer.current.env;
    pyEnv["calendar.event"]._views = {
        calendar: /* xml */ `
            <calendar js_class="attendee_calendar" date_start="start" date_stop="stop" mode="month">
                <field name="partner_ids" filters="1" widget="many2manyattendeeexpandable"
                    write_model="calendar.filters" write_field="partner_id" filter_field="active"/>
                <field name="name"/>
            </calendar>
        `,
        list: arch,
        search: "<search/>",
    };
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "calendar.event",
        views: [
            [false, "calendar"],
            [false, "list"],
        ],
    });
    await contains(".o_switch_view.o_list").click();
    expect.verifySteps([
        "get_selected_calendars_partner_ids",
        [["partner_ids", "in", [serverState.partnerId]]],
    ]);
});
