/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("activity", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("activity click on Reschedule", async function (assert) {
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
    const { openFormView } = await start();
    await openFormView({
        res_model: "res.partner",
        res_id: resPartnerId,
    });
    await click(".btn:contains('Reschedule')");
    assert.containsOnce(target, ".o_calendar_view");
});
