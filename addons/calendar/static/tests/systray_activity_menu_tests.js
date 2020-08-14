odoo.define('calendar.systray.ActivityMenuTests', function (require) {
"use strict";

const { afterEach, beforeEach } = require('mail/static/src/utils/test_utils.js');
const ActivityMenu = require('mail.systray.ActivityMenu');
const testUtils = require('web.test_utils');

const { createComponent } = testUtils;


QUnit.module('calendar', {}, function () {
QUnit.module('ActivityMenu', {
    beforeEach() {
        beforeEach(this);

        Object.assign(this.data, {
            'calendar.event': {
                fields: { // those are all fake, this is the mock of a formatter
                    meetings: { type: 'binary' },
                    model: { type: 'char' },
                    name: { type: 'char', required: true },
                    type: { type: 'char' },
                },
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
                    }, {
                        id: 2,
                        res_model: "calendar.event",
                        name: "meeting2",
                        start: "2018-04-20 09:30:00",
                        allday: false,
                    }]
                }],
            },
        });
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('activity menu widget:today meetings', async function (assert) {
    assert.expect(6);
    const self = this;

    const activityMenu = await createComponent(ActivityMenu, {
        data: this.data,
        mockRPC: function (route, args) {
            if (args.method === "systray_get_activities") {
                return Promise.resolve(self.data["calendar.event"]["records"]);
            }
            return this._super(route, args);
        },
        intercepts: {
            "do-action": (ev) => {
                assert.strictEqual(
                    ev.detail.action,
                    "calendar.action_calendar_event",
                    "should open meeting calendar view in day mode"
                );
            },
        },
        session: {
            async user_has_group(group) {},
        },
    });

    await activityMenu.mount(document.querySelector("#qunit-fixture"));

    assert.hasClass(activityMenu.el, 'o_mail_systray_item', 'should be the instance of widget');

    await testUtils.dom.click(activityMenu.el.querySelector('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.el.querySelector('.o_mail_preview'));

    assert.ok(activityMenu.el.querySelector('.o_meeting_filter'), "should be a meeting");
    assert.containsN(activityMenu, '.o_meeting_filter', 2, 'there should be 2 meetings');
    assert.hasClass(activityMenu.el.querySelector('.o_meeting_filter'), 'o_meeting_bold',
        'this meeting is yet to start');
    assert.doesNotHaveClass(activityMenu.el.querySelectorAll('.o_meeting_filter')[1], 'o_meeting_bold',
        'this meeting has been started');

    activityMenu.destroy();
});
});

});
