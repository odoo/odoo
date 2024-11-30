import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    assertSteps,
    click,
    contains,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { mockService, preloadBundle, serverState } from "@web/../tests/web_test_helpers";
import { actionService } from "@web/webclient/actions/action_service";

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

test("activity menu widget:today meetings", async () => {
    mockDate(2018, 3, 20, 6, 0, 0);
    const pyEnv = await startServer();
    const attendeeId = pyEnv["calendar.attendee"].create({ partner_id: serverState.partnerId });
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
    mockService("action", () => {
        const ogService = actionService.start(getMockEnv());
        return {
            ...ogService,
            doAction(action) {
                if (action?.res_model !== "res.partner") {
                    step("action");
                    expect(action).toBe("calendar.action_calendar_event");
                }
            },
        };
    });
    await start();
    await contains(".o_menu_systray i[aria-label='Activities']");
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityGroup div[name='activityTitle']", { text: "Today's Meetings" });
    await contains(".o-mail-ActivityGroup .o-calendar-meeting", { count: 2 });
    await contains(".o-calendar-meeting span.fw-bold", { text: "meeting1" });
    await contains(".o-calendar-meeting span:not(.fw-bold)", { text: "meeting2" });
    await click(".o-mail-ActivityMenu .o-mail-ActivityGroup");
    await assertSteps(["action"]);
});
