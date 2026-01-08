/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.test("activity menu widget:today meetings", async function (assert) {
    patchDate(2018, 3, 20, 6, 0, 0);
    const pyEnv = await startServer();
    const attendeeId = pyEnv["calendar.attendee"].create({ partner_id: pyEnv.currentPartnerId });
    pyEnv["calendar.event"].create([
        {
            res_model: "calendar.event",
            name: "meeting1",
            start: "2018-04-20 06:30:00",
            attendee_ids: [attendeeId],
        },
        {
            res_model: "calendar.event",
            name: "meeting2",
            start: "2018-04-20 09:30:00",
            attendee_ids: [attendeeId],
        },
    ]);
    const { env } = await start();
    await contains(".o_menu_systray i[aria-label='Activities']");
    await click(".o_menu_systray i[aria-label='Activities']");
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(action, "calendar.action_calendar_event");
            assert.step("action");
        },
    });
    await contains(".o-mail-ActivityGroup div[name='activityTitle']", { text: "Today's Meetings" });
    await contains(".o-mail-ActivityGroup .o-calendar-meeting", { count: 2 });
    await contains(".o-calendar-meeting span.fw-bold", { text: "meeting1" });
    await contains(".o-calendar-meeting span:not(.fw-bold)", { text: "meeting2" });
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup");
    assert.verifySteps(["action"]);
});
