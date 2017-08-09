odoo.define('mail.systray_tests', function (require) {
"use strict";

var systray = require('mail.systray');
var testUtils = require('web.test_utils');


QUnit.module('mail', {}, function () {

QUnit.module('ActivityMenu', {
    beforeEach: function () {

        this.data = {
            'mail.activity.menu': {
                fields: {
                    name: { type: "char" },
                    res_model: { type: "char" },
                    planned_count: { type: "integer"},
                    today_count: { type: "integer"},
                    overdue_count: { type: "integer"},
                    total_count: { type: "integer"},
                },
                records: [{
                        name: "Contact",
                        res_model: "res.partner",
                        planned_count: 0,
                        today_count: 1,
                        overdue_count: 0,
                        total_count: 1,
                    },
                    {
                        name: "Task",
                        res_model: "project.task",
                        planned_count: 1,
                        today_count: 0,
                        overdue_count: 0,
                        total_count: 1,
                    },
                    {
                        name: "Issue",
                        res_model: "project.issue",
                        planned_count: 1,
                        today_count: 1,
                        overdue_count: 0,
                        total_count: 2,
                    }],
                },
            };
        }
    });

QUnit.test('activity menu widget: menu with no records', function (assert) {
    assert.expect(1);

    var activityMenu = new systray.ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        mockRPC: function (route, args) {
            if (args.method === 'activity_user_count') {
                return $.when([]);
            }
            return this._super(route, args);
            },
        });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$('.o_no_activity').hasClass('o_no_activity'), "should not have instance of widget");
    activityMenu.destroy();
});

QUnit.test('activity menu widget: activity menu with 3 records', function (assert) {
    assert.expect(4);
    var self = this;
    var activityMenu = new systray.ActivityMenu();

    testUtils.addMockEnvironment(activityMenu, {
        mockRPC: function (route, args) {
            if (args.method === 'activity_user_count') {
                return $.when(self.data['mail.activity.menu']['records']);
            }
            return this._super(route, args);
            },
        });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$el.hasClass('o_mail_navbar_item'), 'should be the instance of widget');
    assert.ok(activityMenu.$('.o_mail_channel_preview').hasClass('o_mail_channel_preview'), "should instance of widget");
    assert.ok(activityMenu.$('.o_notification_counter').hasClass('o_notification_counter'), "widget should have notification counter");
    assert.strictEqual(parseInt(activityMenu.el.innerText), 4, "widget should have 4 notification counter");
    activityMenu.destroy();
});
});
});
