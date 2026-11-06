import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import {
    editSearch,
    makeMockServer,
    mountView,
    onRpc,
    serverState,
    validateSearch,
} from "@web/../tests/web_test_helpers";

defineCalendarModels();

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
    // Partner 1 is the only attendee checked in the calendar view's sidebar.
    pyEnv["calendar.filters"].create([
        { partner_id: partnerId_1, partner_checked: true, user_id: serverState.userId },
        { partner_id: partnerId_2, partner_checked: false, user_id: serverState.userId },
    ]);
    pyEnv["calendar.event"].create([
        { name: "Meeting 1", partner_ids: [partnerId_1] },
        { name: "Meeting 2", partner_ids: [partnerId_2] },
    ]);
    // Set by the attendee calendar view (see `loadFilterSection`) once it has been opened.
    serverState.userContext = { calendar_filters: { all: false, user: true } };
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
    await mountView({ type: "list", resModel: "calendar.event", arch, domain });
    expect.verifySteps([domain]);
    expect(".o_data_row").toHaveCount(1);
    expect(".o_data_cell[name='name']").toHaveText("Meeting 2");
});
