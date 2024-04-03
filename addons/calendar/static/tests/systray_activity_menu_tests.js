/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module('calendar', {}, function () {
QUnit.module('ActivityMenu');

QUnit.test('activity menu widget:today meetings', async function (assert) {
    assert.expect(6);

    patchDate(2018, 3, 20, 6, 0, 0);
    const pyEnv = await startServer();
    const calendarAttendeeId1 = pyEnv['calendar.attendee'].create({ partner_id: pyEnv.currentPartnerId });
    pyEnv['calendar.event'].create([
        {
            res_model: "calendar.event",
            name: "meeting1",
            start: "2018-04-20 06:30:00",
            attendee_ids: [calendarAttendeeId1],
        },
        {
            res_model: "calendar.event",
            name: "meeting2",
            start: "2018-04-20 09:30:00",
            attendee_ids: [calendarAttendeeId1],
        },
    ]);
    const { click, env } = await start();
    assert.containsOnce(document.body, '.o_ActivityMenuView', 'should contain an instance of widget');

    await click('.dropdown-toggle[title="Activities"]');

    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(action, "calendar.action_calendar_event", 'should open meeting calendar view in day mode');
        },
    });

    assert.ok(document.querySelector('.o_meeting_filter'), "should be a meeting");
    assert.containsN(document.body, '.o_meeting_filter', 2, 'there should be 2 meetings');
    assert.hasClass(document.querySelector('.o_meeting_filter'), 'o_meeting_bold', 'this meeting is yet to start');
    assert.doesNotHaveClass(document.querySelectorAll('.o_meeting_filter')[1], 'o_meeting_bold', 'this meeting has been started');

    await click('.o_ActivityMenuView_activityGroup');
});
});
