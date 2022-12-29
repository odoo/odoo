/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";
import { getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";

let target;

QUnit.module("calender activity menu", {
    async beforeEach() {
        target = getFixture();
    },
});
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
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    await click(".o_menu_systray i[aria-label='Activities']");
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(action, "calendar.action_calendar_event");
            assert.step("action");
        },
    });
    assert.containsOnce(target, ".o-mail-activity-group:contains(Today's Meetings)");
    assert.containsN(target, ".o-mail-activity-group .o-calendar-metting", 2);
    assert.containsOnce(target, ".o-calendar-metting:contains(meeting1)");
    assert.containsOnce(target, ".o-calendar-metting:contains(meeting2)");
    assert.hasClass($(target).find("span:contains(meeting1)"), "fw-bold");
    assert.doesNotHaveClass($(target).find("span:contains(meeting2)"), "fw-bold");
    await click(".o-mail-activity-menu .o-mail-activity-group");
    assert.verifySteps(["action"]);
});
