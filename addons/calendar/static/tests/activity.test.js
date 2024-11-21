import { test } from "@odoo/hoot";
import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    click,
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

defineCalendarModels();

test("activity click on Reschedule", async () => {
    registerArchs({ "calendar.event,false,calendar": `<calendar date_start="start"/>` });
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({});
    const meetingActivityTypeId = pyEnv["mail.activity.type"].create({
        icon: "fa-calendar",
        name: "Meeting",
    });
    const calendarAttendeeId = pyEnv["calendar.attendee"].create({
        partner_id: resPartnerId,
    });
    const calendaMeetingId = pyEnv["calendar.event"].create({
        res_model: "calendar.event",
        name: "meeting1",
        start: "2022-07-06 06:30:00",
        attendee_ids: [calendarAttendeeId],
    });
    pyEnv["mail.activity"].create({
        name: "Small Meeting",
        activity_type_id: meetingActivityTypeId,
        can_write: true,
        res_id: resPartnerId,
        res_model: "res.partner",
        calendar_event_id: calendaMeetingId,
    });
    await start();
    await openFormView("res.partner", resPartnerId);
    await click(".btn", { text: "Reschedule" });
    await contains(".o_calendar_view");
});

test("Can cancel activity linked to an event", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Milan Kundera" });
    const activityTypeId = pyEnv["mail.activity.type"].create({
        icon: "fa-calendar",
        name: "Meeting",
    });
    const attendeeId = pyEnv["calendar.attendee"].create({
        partner_id: partnerId,
    });
    const calendaMeetingId = pyEnv["calendar.event"].create({
        res_model: "calendar.event",
        name: "meeting1",
        start: "2022-07-06 06:30:00",
        attendee_ids: [attendeeId],
    });
    pyEnv["mail.activity"].create({
        name: "Small Meeting",
        activity_type_id: activityTypeId,
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
        calendar_event_id: calendaMeetingId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity .btn", { text: "Cancel" });
    await contains(".o-mail-Activity", { count: 0 });
});
