odoo.define('calendar.systray.ActivityMenuTests', function (require) {
"use strict";

var ActivityMenu = require('mail.systray.ActivityMenu');
var mailUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');


QUnit.module('calendar', {}, function () {

QUnit.module('ActivityMenu', {
    beforeEach: function () {
        this.services = mailUtils.getMailServices();
        this.data = {
            'calendar.event': {
                records: [{
                    name: "Today's meeting (3)",
                    model: "calendar.event",
                    type: 'meeting',
                    meetings: [{
                        id: 1,
                        res_model: "calendar.event",
                        name: "meeting1",
                        start: "2018-04-20 06:30:00",
                        allday: false,
                    },{
                        id: 2,
                        res_model: "calendar.event",
                        name: "meeting2",
                        start: "2018-04-20 09:30:00",
                        allday: false,
                    }]
                }],
            },
        };
    }
});

QUnit.test('activity menu widget:today meetings', async function (assert) {
    assert.expect(6);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.mock.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return Promise.resolve(self.data['calendar.event']['records']);
            }
            return this._super(route, args);
        },
    });

    await activityMenu.appendTo($('#qunit-fixture'));

    assert.hasClass(activityMenu.$el,'o_mail_systray_item', 'should be the instance of widget');

    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));

    testUtils.mock.intercept(activityMenu, 'do_action', function (event) {
        assert.strictEqual(event.data.action,  "calendar.action_calendar_event", 'should open meeting calendar view in day mode');
    });
    await testUtils.dom.click(activityMenu.$('.o_mail_preview'));

    assert.ok(activityMenu.$('.o_meeting_filter'), "should be a meeting");
    assert.containsN(activityMenu, '.o_meeting_filter', 2, 'there should be 2 meetings');
    assert.hasClass(activityMenu.$('.o_meeting_filter').eq(0), 'o_meeting_bold', 'this meeting is yet to start');
    assert.doesNotHaveClass(activityMenu.$('.o_meeting_filter').eq(1), 'o_meeting_bold', 'this meeting has been started');
    activityMenu.destroy();
});
});
});
