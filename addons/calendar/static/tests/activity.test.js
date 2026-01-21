import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    click,
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { serializeDateTime } from "@web/core/l10n/dates";
import { clickEvent } from "@web/../tests/views/calendar/calendar_test_helpers";
import { preloadBundle } from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

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

test("Can delete activity linked to an event", async () => {
    registerArchs({ "calendar.event,false,calendar": `<calendar date_start="start"/>` });
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
        start: serializeDateTime(DateTime.now().plus({ days: 1 })),
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
    await click(".o-mail-Activity .btn", { text: "Reschedule" });
    await contains(".o_calendar_view");
    await animationFrame();
    await clickEvent(calendaMeetingId);
    await click(".o-overlay-container .o_cw_popover_delete");
    await click(".o_dialog .modal-footer button.btn.btn-danger");
    await contains(`.o_event[data-event-id="${calendaMeetingId}"]`, { count: 0 });
});
