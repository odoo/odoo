import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { ResPartner } from "@mail/../tests/mock_server/mock_models/res_partner";
import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    makeMockServer,
    mountView,
    selectFieldDropdownItem,
} from "@web/../tests/web_test_helpers";
import { getOrigin } from "@web/core/utils/urls";

defineCalendarModels();

const DISCUSS_LOCATION = `${getOrigin()}/calendar/join_videocall/testtoken`;

const ARCH = /* xml */ `
    <form js_class="calendar_form">
        <field name="access_token" force_save="1" invisible="1"/>
        <field name="videocall_source" force_save="1" invisible="1"/>
        <field name="videocall_location" force_save="1"/>
        <button name="clear_videocall_location" type="object" string="Remove"/>
        <field name="partner_ids" widget="many2many_tags"/>
    </form>
`;

const serverData = {};

beforeEach(async () => {
    // On small screens, attendees are picked in a dialog listing the partners as
    // kanban cards instead of in the inline autocomplete dropdown.
    ResPartner._views.kanban = /* xml */ `
        <kanban>
            <templates>
                <t t-name="card"><field name="name"/></t>
            </templates>
        </kanban>
    `;
    ResPartner._views.search = /* xml */ `<search/>`;
    const { env: pyEnv } = await makeMockServer();
    [serverData.organizerId, serverData.attendeeId] = pyEnv["res.partner"].create([
        { name: "Zeus" },
        { name: "Azdaha" },
        { name: "Hydra" },
    ]);
    serverData.eventId = pyEnv["calendar.event"].create({
        name: "event 1",
        partner_ids: [serverData.organizerId],
    });
});

async function addAttendee(name) {
    await selectFieldDropdownItem("partner_ids", name);
    await animationFrame();
}

test("a video call link is generated once a meeting has a second attendee", async () => {
    await mountView({
        type: "form",
        resModel: "calendar.event",
        resId: serverData.eventId,
        arch: ARCH,
    });
    expect(".o_field_many2many_tags .o_tag").toHaveCount(1);
    expect("[name=videocall_location]").toHaveText("");

    await addAttendee("Azdaha");

    expect(".o_field_many2many_tags .o_tag").toHaveCount(2);
    expect("[name=videocall_location]").toHaveText(DISCUSS_LOCATION);
});

test("a meeting created with several attendees already has a video call link", async () => {
    await mountView({
        type: "form",
        resModel: "calendar.event",
        arch: ARCH,
        context: {
            default_partner_ids: [serverData.organizerId, serverData.attendeeId],
        },
    });
    expect(".o_field_many2many_tags .o_tag").toHaveCount(2);
    expect("[name=videocall_location]").toHaveText(DISCUSS_LOCATION);
});

test("a meeting the organizer attends alone gets no video call link", async () => {
    await mountView({
        type: "form",
        resModel: "calendar.event",
        arch: ARCH,
        context: { default_partner_ids: [serverData.organizerId] },
    });
    expect(".o_field_many2many_tags .o_tag").toHaveCount(1);
    expect("[name=videocall_location]").toHaveText("");
});

test("a video call link removed by hand is not brought back by a new attendee", async () => {
    await mountView({
        type: "form",
        resModel: "calendar.event",
        resId: serverData.eventId,
        arch: ARCH,
    });
    await addAttendee("Azdaha");
    expect("[name=videocall_location]").toHaveText(DISCUSS_LOCATION);

    await contains("button[name=clear_videocall_location]").click();
    expect("[name=videocall_location]").toHaveText("");
    await addAttendee("Hydra");

    expect(".o_field_many2many_tags .o_tag").toHaveCount(3);
    expect("[name=videocall_location]").toHaveText("");
});
