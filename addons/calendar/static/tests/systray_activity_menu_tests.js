/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';
import ActivityMenu from '@mail/js/systray/systray_activity_menu';

import testUtils from 'web.test_utils';
import { patchDate } from "@web/../tests/helpers/utils";

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
    const { widget } = await start();

    const activityMenu = new ActivityMenu(widget);
    await activityMenu.appendTo($('#qunit-fixture'));

    assert.hasClass(activityMenu.$el, 'o_mail_systray_item', 'should be the instance of widget');

    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));

    testUtils.mock.intercept(activityMenu, 'do_action', function (event) {
        assert.strictEqual(event.data.action, "calendar.action_calendar_event", 'should open meeting calendar view in day mode');
    });
    await testUtils.dom.click(activityMenu.$('.o_mail_preview'));

    assert.ok(activityMenu.$('.o_meeting_filter'), "should be a meeting");
    assert.containsN(activityMenu, '.o_meeting_filter', 2, 'there should be 2 meetings');
    assert.hasClass(activityMenu.$('.o_meeting_filter').eq(0), 'o_meeting_bold', 'this meeting is yet to start');
    assert.doesNotHaveClass(activityMenu.$('.o_meeting_filter').eq(1), 'o_meeting_bold', 'this meeting has been started');
    widget.destroy();
});
});
