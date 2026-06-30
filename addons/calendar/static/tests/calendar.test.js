import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { contains, makeMockServer, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { getOrigin } from "@web/core/utils/urls";

defineCalendarModels();

const serverData = {};

beforeEach(async () => {
    const { env: pyEnv } = await makeMockServer();
    serverData.partnerIds = pyEnv["res.partner"].create([{ name: "Zeus" }, { name: "Azdaha" }]);
    serverData.eventId = pyEnv["calendar.event"].create({
        name: "event 1",
        partner_ids: serverData.partnerIds,
    });
});

test("Many2ManyAttendee: basic rendering", async () => {
    onRpc("get_attendee_detail", (request) => {
        expect.step("get_attendee_detail");
        expect(request.model).toBe("res.partner");
        expect(request.args[0]).toEqual(serverData.partnerIds);
        expect(request.args[1]).toEqual([serverData.eventId]);
        return [
            { id: serverData.partnerIds[0], name: "Zeus", status: "accepted", color: 0 },
            { id: serverData.partnerIds[1], name: "Azdaha", status: "tentative", color: 0 },
        ];
    });
    await mountView({
        type: "form",
        resModel: "calendar.event",
        resId: serverData.eventId,
        arch: /*xml*/ `
            <form>
                <field name="partner_ids" widget="many2manyattendee"/>
            </form>
        `,
    });
    expect(".o_field_widget[name='partner_ids'] div.o_field_tags").toHaveCount(1);
    expect(".o_field_widget[name='partner_ids'] .o_tag").toHaveCount(2);
    expect(".o_field_widget[name='partner_ids'] .o_tag:eq(0)").toHaveText("Zeus");
    expect(
        ".o_field_widget[name='partner_ids'] .o_tag:eq(0) .attendee_tag_status.o_attendee_status_accepted"
    ).toHaveCount(1);
    expect(".o_field_widget[name='partner_ids'] .o_tag:eq(1)").toHaveText("Azdaha");
    expect(
        ".o_field_widget[name='partner_ids'] .o_tag:eq(1) .attendee_tag_status.o_attendee_status_tentative"
    ).toHaveCount(1);
    expect(".o_field_widget[name='partner_ids'] .o_tag:eq(0) img").toHaveCount(1);
    expect(".o_field_widget[name='partner_ids'] .o_tag:eq(0) img").toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/res.partner/${serverData.partnerIds[0]}/avatar_128`
    );
    expect.verifySteps(["get_attendee_detail"]);
});

test("Many2ManyAttendee: remove own attendee", async () => {
    onRpc("get_attendee_detail", () => [
        { id: serverData.partnerIds[0], name: "Zeus", status: "accepted", color: 0 },
        { id: serverData.partnerIds[1], name: "Azdaha", status: "tentative", color: 0 },
    ]);
    await mountView({
        type: "form",
        resModel: "calendar.event",
        resId: serverData.eventId,
        arch: /*xml*/ `
            <form>
                <field name="partner_ids" widget="many2manyattendee"/>
            </form>
        `,
    });
    expect(".o_field_widget[name='partner_ids'] .o_tag").toHaveCount(2);

    // Attendee must be able to uninvite itself from the event.
    await contains(".o_field_widget[name='partner_ids'] .o_delete", { visible: false }).click();
    await contains(".o_form_button_save").click();
    expect(".o_field_widget[name='partner_ids'] .o_tag").toHaveCount(1);
});
