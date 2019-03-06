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

QUnit.test('activity menu widget:today meetings', function (assert) {
    assert.expect(8);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return $.when(self.data['calendar.event']['records']);
            }
            return this._super(route, args);
        },
    });

    activityMenu.appendTo($('#qunit-fixture'));

    assert.ok(activityMenu.$el.hasClass('o_mail_systray_item'), 'should be the instance of widget');

    testUtils.intercept(activityMenu, 'do_action', function (event) {
        assert.ok(true, "should have triggered a do_action");
        assert.strictEqual(event.data.action.res_id,  activityMenu.$('.o_meeting_filter').eq(0).data('res_id'), 'should open particular meeting form view');
    });
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$('.o_meeting_filter').eq(0).click();

    testUtils.intercept(activityMenu, 'do_action', function (event) {
        assert.strictEqual(event.data.action,  "calendar.action_calendar_event", 'should open meeting calendar view in day mode');
    });
    activityMenu.$('.o_mail_preview').click();

    assert.ok(activityMenu.$('.o_meeting_filter'), "should be a meeting");
    assert.strictEqual(activityMenu.$('.o_meeting_filter').length, 2, 'there should be 2 meetings');
    assert.strictEqual(activityMenu.$('.o_meeting_filter').eq(0).hasClass('o_meeting_bold'), true, 'this meeting is yet to start');
    assert.strictEqual(activityMenu.$('.o_meeting_filter').eq(1).hasClass('o_meeting_bold'), false, 'this meeting has been started');
    activityMenu.destroy();
});
});
});
