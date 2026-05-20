import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    click,
    contains,
    openListView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { preloadBundle } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

test("list activity widget: reschedule button in dropdown", async () => {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({});
    const userId = pyEnv["res.users"].create({ partner_id: resPartnerId });
    const activityTypeId = pyEnv["mail.activity.type"].create({
        icon: "fa-calendar",
        name: "Meeting",
    });
    const tomorrow = serializeDateTime(DateTime.now().plus({ days: 1 }));
    const attendeeId = pyEnv["calendar.attendee"].create({ partner_id: resPartnerId });
    const meetingId = pyEnv["calendar.event"].create({
        res_model: "calendar.event",
        name: "meeting1",
        start: tomorrow,
        attendee_ids: [attendeeId],
    });
    const activityId_1 = pyEnv["mail.activity"].create({
        name: "OXP",
        activity_type_id: activityTypeId,
        date_deadline: tomorrow,
        state: "planned",
        can_write: true,
        res_id: userId,
        res_model: "res.users", //Target the user instead of the partner
        calendar_event_id: meetingId,
        summary: "OXP",
    });
    pyEnv["res.users"].write([userId], {
        activity_ids: [activityId_1],
        activity_state: "today",
        // activity_summary: "OXP",
    });

    // FIXME: Manually trigger recomputation of related fields
    pyEnv["res.users"]._applyComputesAndValidate();
    pyEnv["res.users"][0].activity_ids = [activityId_1];

    await start();
    await openListView("res.users", {
        arch: `<list>
            <field name="activity_ids" widget="list_activity"/>
        </list>`,
        // Filter the view so we only click the button for our specific test user
        domain: [["id", "=", userId]],
    });
    await contains(".o-mail-ListActivity-summary", { text: "OXP" });
    await click(".o-mail-ActivityButton"); // open the popover
    await contains(".o-mail-ActivityListPopoverItem-editbtn .fa-pencil", { count: 0 });
    await contains(".o-mail-ActivityListPopoverItem-editbtn .fa-calendar");
});
